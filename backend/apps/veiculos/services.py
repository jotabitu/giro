"""Regras dos veículos, categorias, preços e extras (VEI-01 a VEI-07, LOC-01, LOC-02, LOC-15,
PLT-03). Único lugar que grava nestes models.

Interface para os outros apps (contrato de veículos, "Eventos e interface interna"):
`transicionar`, `atualizar_km` e `receber_na_troca`. Locações, vistorias, manutenção e vendas
mudam o status do veículo só por `transicionar`.
"""

import logging
import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import Max
from django.db.models.functions import Lower

from apps.filiais import selectors as filiais_selectors
from apps.filiais.models import Filial
from apps.notificacoes.services import avisar
from apps.plataforma.services import atualizar_uso, exigir_limite, registrar_passo_implantacao
from comum import aprovacoes, arquivos, comprovante_leitura, estados, leituras, relogio
from comum.auditoria import Categoria as CategoriaAuditoria
from comum.auditoria import (
    TipoAtor,
    ator_atual,
    auditar,
    diferenca,
    registrar_evento,
    retrato,
)
from comum.documentos import placa_com_hifen
from comum.erros import (
    Conflito,
    ErroDeRegra,
    ErroDeValidacao,
    NaoEncontrado,
    TransicaoInvalida,
)
from comum.eventos import publicar

from .models import (
    CAMPOS_DA_VEI_09,
    DOCUMENTOS_QUE_BLOQUEIAM,
    FORA_DA_FROTA,
    LIMITE_DA_GALERIA,
    MOVIMENTAVEIS,
    TRANSICOES_VEICULO,
    Categoria,
    DocumentoVeiculo,
    Especie,
    Extra,
    FotoVeiculo,
    HistoricoStatusVeiculo,
    LeituraKm,
    Origem,
    PrecoCategoria,
    StatusVeiculo,
    TipoDocumento,
    TipoVeiculo,
    TransferenciaVeiculo,
    Veiculo,
)

S = StatusVeiculo
logger = logging.getLogger(__name__)
ALVO_CATEGORIA = "veiculos.Categoria"
# Placa antiga (ABC1234) ou Mercosul (ABC1D23), sem hífen.
PLACA = re.compile(r"^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$")
CHASSI = re.compile(r"^[A-Z0-9]{17}$")
ANO_MINIMO = 1950

# Verbo de cada destino, para "Não é possível <ação> um veículo <status>".
_VERBO = {
    S.DISPONIVEL: "liberar",
    S.RESERVADO: "reservar",
    S.ALUGADO: "alugar",
    S.EM_MANUTENCAO: "mandar para a manutenção",
    S.INDISPONIVEL: "bloquear",
    S.A_VENDA: "colocar à venda",
    S.VENDIDO: "vender",
    S.BAIXADO: "baixar",
    S.EM_MOVIMENTACAO: "movimentar",
}
MOTIVOS_DE_BAIXA = {
    "perda_total": "Perda total",
    "roubo": "Roubo",
    "sucata": "Sucata",
    "outro": "Outro",
}


@dataclass(frozen=True)
class OrigemDaMudanca:
    """Origem genérica da mudança (ADR 0011): `OrigemDaMudanca("locacao", 2841, "LOC-2841")`."""

    tipo: str
    id: int | None = None
    codigo: str = ""


MANUAL = OrigemDaMudanca(Origem.MANUAL)


def _quem() -> int | None:
    ator = ator_atual()
    return ator.id if ator.tipo == TipoAtor.USUARIO else None


def _origem(origem: OrigemDaMudanca) -> dict[str, Any]:
    return {"origem_tipo": origem.tipo, "origem_id": origem.id, "origem_codigo": origem.codigo}


def formatar_km(km: int) -> str:
    return f"{km:,}".replace(",", ".")


def travar(veiculo: Veiculo) -> Veiculo:
    """A linha do veículo travada até o fim da transação: movimentação e locação conferem o
    status com ela (ADR 0028, item 3)."""
    travado: Veiculo = Veiculo.objects.select_for_update().get(pk=veiculo.pk)
    return travado


_travar = travar


def _recarregar(veiculo: Veiculo) -> None:
    """O objeto de quem chamou passa a ter o que foi gravado pela cópia travada."""
    veiculo.refresh_from_db()
    veiculo._status_salvo = veiculo.status


# --- Status (seção "Veículos" das regras) ---


def transicao_invalida(de: str, para: str) -> TransicaoInvalida:
    status = StatusVeiculo(de).label.lower()
    return TransicaoInvalida(
        "transicao_veiculo",
        f"Não é possível {_VERBO[S(para)]} um veículo {status}",
        {"de": de, "para": para},
    )


def transicionar(
    veiculo: Veiculo,
    novo_status: str,
    *,
    origem: OrigemDaMudanca,
    motivo: str | None = None,
    acao: str | None = None,
) -> Veiculo:
    """O único caminho para mudar o status: confere a tabela de transições, grava o
    `HistoricoStatusVeiculo` e a auditoria. Fora da tabela: 409 `transicao_veiculo`.

    Sair da empresa (`vendido`, `baixado`) devolve uma vaga do plano, e voltar dela ocupa uma
    (PLT-03); a volta não é recusada pelo limite, porque vem de uma venda já feita.
    """
    with transaction.atomic():
        travado = _travar(veiculo)
        de = travado.status
        if novo_status not in TRANSICOES_VEICULO.get(de, set()):
            raise transicao_invalida(de, novo_status)
        travado.motivo_status = (motivo or "")[:200]
        estados.transicionar(
            travado,
            novo_status,
            motivo=motivo or "",
            acao=f"veiculo.{acao or novo_status}",
            regra="VEI-07" if de == S.VENDIDO else "",
        )
        travado.save(update_fields=["motivo_status", "atualizado_em"])
        HistoricoStatusVeiculo.objects.create(
            veiculo=travado,
            de=de,
            para=novo_status,
            em=relogio.agora(),
            por_id=_quem(),
            motivo=(motivo or "")[:200],
            **_origem(origem),
        )
        if de not in FORA_DA_FROTA and novo_status in FORA_DA_FROTA:
            atualizar_uso("veiculos", -1)
        elif de in FORA_DA_FROTA and novo_status not in FORA_DA_FROTA:
            atualizar_uso("veiculos", 1)
    _recarregar(veiculo)
    return veiculo


def _exigir_motivo(motivo: str | None, campo: str = "motivo") -> str:
    texto = (motivo or "").strip()
    if not texto:
        raise ErroDeValidacao({campo: ["Informe o motivo."]})
    return texto


def bloquear(veiculo: Veiculo, motivo: str) -> Veiculo:
    return transicionar(
        veiculo, S.INDISPONIVEL, origem=MANUAL, motivo=_exigir_motivo(motivo), acao="bloquear"
    )


def desbloquear(veiculo: Veiculo, motivo: str | None = None) -> Veiculo:
    """`indisponivel` → `disponivel`. Com CRLV ou seguro ativo vencido: 422 `VEI-03`."""
    with transaction.atomic():
        travado = _travar(veiculo)
        if travado.status != S.INDISPONIVEL:
            raise transicao_invalida(travado.status, S.DISPONIVEL)
        vencidos = documentos_vencidos_que_bloqueiam(travado, relogio.hoje())
        if vencidos:
            raise documento_vencido(vencidos)
        transicionar(
            travado, S.DISPONIVEL, origem=MANUAL, motivo=(motivo or "").strip(), acao="desbloquear"
        )
    _recarregar(veiculo)
    return veiculo


def colocar_a_venda(
    veiculo: Veiculo, valor_venda_centavos: int, referencia_fipe_centavos: int | None = None
) -> Veiculo:
    """`disponivel` → `a_venda` (VEN-01). A Frota passa a mostrar o valor de venda."""
    with transaction.atomic():
        transicionar(veiculo, S.A_VENDA, origem=MANUAL, acao="colocar_a_venda")
        with auditar(veiculo, "veiculo.definir_valor_venda", CategoriaAuditoria.OPERACAO):
            veiculo.valor_venda_centavos = valor_venda_centavos
            veiculo.referencia_fipe_centavos = referencia_fipe_centavos
            veiculo.save(
                update_fields=["valor_venda_centavos", "referencia_fipe_centavos", "atualizado_em"]
            )
    return veiculo


def voltar_para_frota(veiculo: Veiculo) -> Veiculo:
    """`a_venda` → `disponivel`. A recusa com venda aberta (409 `VEN-10`) entra com vendas."""
    if veiculo.status != S.A_VENDA:
        raise transicao_invalida(veiculo.status, S.DISPONIVEL)
    return transicionar(veiculo, S.DISPONIVEL, origem=MANUAL, acao="voltar_para_frota")


def baixar(veiculo: Veiculo, motivo: str, descricao: str) -> Veiculo:
    """Qualquer estado, exceto `alugado`, vai para `baixado` (perda total, roubo, sucata).
    A movimentação aberta do veículo é cancelada pelo assinante de `veiculos.baixado`, na mesma
    transação (MOV-03, decisão do dono de 16 out 2026, opção B)."""
    if motivo not in MOTIVOS_DE_BAIXA:
        raise ErroDeValidacao({"motivo": ["Escolha perda total, roubo, sucata ou outro."]})
    texto = MOTIVOS_DE_BAIXA[motivo]
    if descricao.strip():
        texto = f"{texto}: {descricao.strip()}"
    # "Veículo baixado: roubo" na movimentação cancelada; no `outro`, a descrição (T-311).
    if motivo == "outro":
        motivo_texto = descricao.strip() or "outro"
    else:
        motivo_texto = MOTIVOS_DE_BAIXA[motivo].lower()
    with transaction.atomic():
        transicionar(veiculo, S.BAIXADO, origem=MANUAL, motivo=texto, acao="baixar")
        publicar("veiculos.veiculo_baixado", veiculo_id=veiculo.pk, motivo_texto=motivo_texto)
    return veiculo


# --- Cadastro (VEI-01, PLT-03) ---


def normalizar_placa(placa: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", placa or "").upper()


def normalizar_chassi(chassi: str) -> str:
    return re.sub(r"\s", "", chassi or "").upper()


def _conferir_unicos(placa: str | None, chassi: str | None, exceto: int | None = None) -> None:
    """409 `VEI-01` para placa ou chassi já usados, em qualquer estado do veículo."""
    for campo, valor, rotulo in (("placa", placa, "placa"), ("chassi", chassi, "chassi")):
        if not valor:
            continue
        existente = Veiculo.objects.filter(**{campo: valor}).exclude(pk=exceto).first()
        if existente is not None:
            raise Conflito(
                "VEI-01",
                f"Já existe um veículo com este {rotulo}"
                if campo == "chassi"
                else f"Já existe um veículo com esta {rotulo}",
                {"campo": campo, "veiculo_id": existente.pk},
            )


def _validar_identificacao(
    dados: dict[str, Any], erros: dict[str, list[str]], limpos: dict[str, Any]
) -> None:
    if "placa" in dados:
        limpos["placa"] = normalizar_placa(dados["placa"])
        if not PLACA.match(limpos["placa"]):
            erros["placa"] = ["Placa inválida. Use o padrão ABC1234 ou ABC1D23."]
    if "chassi" in dados:
        limpos["chassi"] = normalizar_chassi(dados["chassi"])
        if not CHASSI.match(limpos["chassi"]):
            erros["chassi"] = ["O chassi tem 17 letras e números."]


def _categoria_para(
    categoria_id: Any, filial_id: int, erros: dict[str, list[str]]
) -> Categoria | None:
    categoria: Categoria | None = Categoria.ativos.filter(pk=categoria_id).first()
    if categoria is None or categoria.filial_id not in (None, filial_id):
        erros["categoria_id"] = ["Escolha uma categoria ativa desta filial."]
        return None
    return categoria


def _validar_dados(
    dados: dict[str, Any], filial_id: int, erros: dict[str, list[str]], limpos: dict[str, Any]
) -> None:
    for campo in ("marca", "modelo", "cor"):
        if campo in dados:
            limpos[campo] = str(dados[campo] or "").strip()
            if not limpos[campo]:
                erros[campo] = ["Campo obrigatório."]
    if "renavam" in dados:
        limpos["renavam"] = re.sub(r"\D", "", dados["renavam"] or "")
        if limpos["renavam"] and len(limpos["renavam"]) != 11:
            erros["renavam"] = ["O Renavam tem 11 dígitos."]
    ano_limite = relogio.hoje().year + 1
    for campo in ("ano_fabricacao", "ano_modelo"):
        if campo in dados:
            limpos[campo] = dados[campo]
            if not ANO_MINIMO <= int(dados[campo]) <= ano_limite:
                erros[campo] = ["Ano inválido."]
    fabricacao = limpos.get("ano_fabricacao")
    modelo = limpos.get("ano_modelo")
    if fabricacao and modelo and not fabricacao <= modelo <= fabricacao + 1:
        erros["ano_modelo"] = ["O ano do modelo é o de fabricação ou o seguinte."]
    if "combustivel" in dados:
        limpos["combustivel"] = dados["combustivel"] or None  # VEI-08; o enum vem do serializer
    if "categoria_id" in dados:
        limpos["categoria"] = _categoria_para(dados["categoria_id"], filial_id, erros)
    for campo in (
        "capacidade_tanque_litros",
        "valor_compra_centavos",
        "data_compra",
        "entrou_na_frota_em",
    ):
        if campo in dados:
            limpos[campo] = dados[campo]
    _validar_vei_09(dados, erros, limpos)


# --- Dados do documento, rastreador e anotações (VEI-09, T-421) ---

MENSAGENS_DA_VEI_09 = {
    "documento.potencia_cv": "Informe a potência em cv, de 1 a 999.",
    "documento.cilindrada_cc": "Informe a cilindrada em cc, de 1 a 9999.",
    "documento.especie": "Escolha a espécie da lista.",
    "documento.tipo": "Use até 30 caracteres.",
    "documento.carroceria": "Use até 30 caracteres.",
    "documento.lotacao": "Informe a lotação em pessoas, de 1 a 99.",
    "documento.peso_bruto_kg": "Informe o peso bruto em kg.",
    "documento.numero_motor": "Use só letras e números, até 21.",
    "documento.observacoes": "Use até 500 caracteres.",
    "rastreador.numero": "Use só letras e números, até 20.",
    "rastreador.empresa": "Use até 60 caracteres.",
    "anotacoes": "Use até 500 caracteres.",
}
FAIXAS_DA_VEI_09 = {
    "documento.potencia_cv": (1, 999),
    "documento.cilindrada_cc": (1, 9999),
    "documento.lotacao": (1, 99),
    "documento.peso_bruto_kg": (1, 99999),
}
TEXTOS_DA_VEI_09 = {
    "documento.tipo": 30,
    "documento.carroceria": 30,
    "documento.observacoes": 500,
    "rastreador.empresa": 60,
    "anotacoes": 500,
}
# Letras e números, em maiúsculas e sem espaços.
CODIGOS_DA_VEI_09 = {"documento.numero_motor": 21, "rastreador.numero": 20}
BLOCOS_DA_VEI_09 = ("documento", "rastreador")


def campos_pontuados(dados: dict[str, Any]) -> dict[str, Any]:
    """Os blocos `documento` e `rastreador` e as `anotacoes` do corpo, nas chaves pontuadas
    (`documento.lotacao`). Só as chaves enviadas: no editar, chave ausente não muda."""
    pontuados: dict[str, Any] = {}
    for bloco in BLOCOS_DA_VEI_09:
        for chave, valor in (dados.get(bloco) or {}).items():
            pontuados[f"{bloco}.{chave}"] = valor
    if "anotacoes" in dados:
        pontuados["anotacoes"] = dados["anotacoes"]
    return {chave: v for chave, v in pontuados.items() if chave in CAMPOS_DA_VEI_09}


def _valor_da_vei_09(chave: str, valor: Any) -> tuple[Any, bool]:
    """O valor limpo e se ele vale. Vazio, `null` ou só espaços apagam (texto vira "")."""
    texto = valor.strip() if isinstance(valor, str) else valor
    if texto is None or texto == "":
        return ("" if chave in TEXTOS_DA_VEI_09 or chave in CODIGOS_DA_VEI_09 else None), True
    if chave in FAIXAS_DA_VEI_09:
        minimo, maximo = FAIXAS_DA_VEI_09[chave]
        if isinstance(texto, bool) or not re.fullmatch(r"\d{1,6}", str(texto)):
            return None, False
        return int(texto), minimo <= int(texto) <= maximo
    if chave == "documento.especie":
        return texto, texto in Especie.values
    if chave in CODIGOS_DA_VEI_09:
        codigo = re.sub(r"\s", "", str(texto)).upper()
        return codigo, bool(re.fullmatch(rf"[A-Z0-9]{{1,{CODIGOS_DA_VEI_09[chave]}}}", codigo))
    return str(texto), len(str(texto)) <= TEXTOS_DA_VEI_09[chave]


def _validar_vei_09(
    dados: dict[str, Any], erros: dict[str, list[str]], limpos: dict[str, Any]
) -> None:
    """Todos opcionais (VEI-01); fora do formato, 400 com a chave pontuada (CA-421-07)."""
    for chave, valor in campos_pontuados(dados).items():
        limpo, vale = _valor_da_vei_09(chave, valor)
        if not vale:
            erros[chave] = [MENSAGENS_DA_VEI_09[chave]]
            continue
        limpos[CAMPOS_DA_VEI_09[chave]] = limpo


def dados_da_vei_09(dados: dict[str, Any]) -> dict[str, Any]:
    """Os campos do model a partir dos blocos (`documento`, `rastreador`, `anotacoes`), para quem
    grava sem passar pelo cadastro (o seed dos testes). Fora do formato: 400."""
    erros: dict[str, list[str]] = {}
    limpos: dict[str, Any] = {}
    _validar_vei_09(dados, erros, limpos)
    if erros:
        raise ErroDeValidacao(erros)
    return limpos


def valores_pontuados(veiculo: Veiculo) -> dict[str, Any]:
    """Os campos da VEI-09 gravados, nas chaves da API (texto vazio vira `None`)."""
    return {chave: getattr(veiculo, campo) or None for chave, campo in CAMPOS_DA_VEI_09.items()}


OBRIGATORIOS_DO_CADASTRO = (
    "placa",
    "chassi",
    "marca",
    "modelo",
    "ano_fabricacao",
    "ano_modelo",
    "cor",
    "categoria_id",
    "filial_id",
)


def _limpar_cadastro(dados: dict[str, Any]) -> dict[str, Any]:
    erros: dict[str, list[str]] = {
        campo: ["Campo obrigatório."]
        for campo in OBRIGATORIOS_DO_CADASTRO
        if dados.get(campo) in (None, "")
    }
    limpos: dict[str, Any] = {}
    filial = Filial.ativos.filter(pk=dados.get("filial_id")).first()
    if filial is None and "filial_id" not in erros:
        erros["filial_id"] = ["Escolha uma filial ativa."]
    limpos["filial"] = filial
    presentes = {chave: valor for chave, valor in dados.items() if valor not in (None, "")}
    _validar_identificacao(presentes, erros, limpos)
    _validar_dados(presentes, filial.pk if filial else 0, erros, limpos)
    km = dados.get("km_atual") or 0
    if int(km) < 0:
        erros["km_atual"] = ["O km não pode ser negativo."]
    limpos["km_atual"] = int(km)
    if erros:
        raise ErroDeValidacao(erros)
    return limpos


def _criar(
    limpos: dict[str, Any],
    status: str,
    origem: OrigemDaMudanca,
    extras_do_evento: dict[str, Any] | None = None,
) -> Veiculo:
    agora = relogio.agora()
    limpos.setdefault("entrou_na_frota_em", relogio.hoje())
    try:
        with transaction.atomic():
            veiculo = Veiculo.objects.create(**limpos, status=status, km_atualizado_em=agora)
    except IntegrityError as erro:  # placa ou chassi numa corrida
        _conferir_unicos(limpos.get("placa"), limpos.get("chassi"))
        raise Conflito("VEI-01", "Já existe um veículo com esta placa ou chassi") from erro
    HistoricoStatusVeiculo.objects.create(
        veiculo=veiculo, de="", para=status, em=agora, por_id=_quem(), **_origem(origem)
    )
    LeituraKm.objects.create(
        veiculo=veiculo, km=veiculo.km_atual, lido_em=agora, por_id=_quem(), **_origem(origem)
    )
    registrar_evento(
        "veiculo.cadastrar",
        CategoriaAuditoria.OPERACAO,
        objeto=veiculo,
        depois={**retrato(veiculo), **(extras_do_evento or {})},
        regra="VEI-01",
    )
    atualizar_uso("veiculos", 1)
    return veiculo


def cadastrar(dados: dict[str, Any], *, origem: OrigemDaMudanca | None = None) -> Veiculo:
    """POST /api/veiculos/: 400 nos campos, 409 `VEI-01` na placa ou no chassi, 422 `PLT-03`
    no limite. Nasce `disponivel`, com o histórico inicial e a primeira leitura de km.

    A importação por planilha (IMP-02) passa `origem=OrigemDaMudanca("importacao", id)`."""
    limpos = _limpar_cadastro(dados)
    with transaction.atomic():
        _conferir_unicos(limpos["placa"], limpos["chassi"])
        exigir_limite("veiculos")
        return _criar(limpos, S.DISPONIVEL, origem or OrigemDaMudanca(Origem.CADASTRO))


MENSAGEM_CRLV_ARQUIVO = "Envie o PDF do CRLV-e, até 2 MB."
CRLV_TAMANHO_MAXIMO = 2 * 1024 * 1024
CRLV_NOME = "CRLV-e.pdf"  # o nome enviado pode trazer o nome da pessoa (ADR 0026, item 9)
# Campo do cadastro → atributo gravado, para comparar com o que a leitura devolveu.
CAMPOS_DO_CRLV = (
    "placa",
    "chassi",
    "renavam",
    "marca",
    "modelo",
    "ano_fabricacao",
    "ano_modelo",
    "cor",
    "combustivel",
)


def _conteudo_do_crlv(arquivo: Any) -> bytes:
    """De novo os primeiros bytes e os 2 MB, sem confiar na leitura (ADR 0026, item 8)."""
    arquivo.seek(0)
    conteudo: bytes = arquivo.read(CRLV_TAMANHO_MAXIMO + 1)
    arquivo.seek(0)
    if len(conteudo) > CRLV_TAMANHO_MAXIMO or not conteudo.startswith(b"%PDF-"):
        raise ErroDeValidacao({"crlv_arquivo": [MENSAGEM_CRLV_ARQUIVO]})
    return conteudo


def cadastrar_com_crlv(
    dados: dict[str, Any],
    arquivo: Any,
    validade: date,
    exercicio: int | None,
    leitura: str | None,
    usuario: Any,
) -> Veiculo:
    """POST /api/veiculos/ em multipart com o CRLV lido (VEI-08, CA-247-03): o veículo e o
    `DocumentoVeiculo` `crlv` numa transação só, com as validações de sempre (VEI-01, PLT-03).

    Com o comprovante `leitura` válido para este arquivo, empresa e pessoa, o evento
    `veiculo.cadastrar` leva `preenchido_pelo_documento` (campos lidos e os corrigidos, sem
    valores). Sem ele, salva do mesmo jeito, sem a marca. Se a transação falhar depois de o
    arquivo ir para o armazenamento, o arquivo é apagado."""
    conteudo = _conteudo_do_crlv(arquivo)
    limpos = _limpar_cadastro(dados)
    resumos = comprovante_leitura.conferir("crlv", leitura, conteudo, usuario)
    extras: dict[str, Any] = {}
    if resumos is not None:
        gravados = {campo: limpos.get(campo) for campo in CAMPOS_DO_CRLV}
        gravados |= {chave: limpos.get(campo) for chave, campo in CAMPOS_DA_VEI_09.items()}
        lidos, corrigidos = comprovante_leitura.campos_do_documento(resumos, conteudo, gravados)
        extras = _preenchido_pelo_documento(lidos, corrigidos)
    gravado: str | None = None  # o nome do arquivo já enviado
    try:
        with transaction.atomic():
            _conferir_unicos(limpos["placa"], limpos["chassi"])
            exigir_limite("veiculos")
            veiculo = _criar(limpos, S.DISPONIVEL, OrigemDaMudanca(Origem.CADASTRO), extras)
            documento = DocumentoVeiculo.objects.create(
                veiculo=veiculo,
                tipo=TipoDocumento.CRLV,
                validade=validade,
                exercicio=exercicio,
                arquivo_nome=CRLV_NOME,
                por_id=_quem(),
            )
            documento.arquivo.save(CRLV_NOME, arquivo, save=True)
            gravado = documento.arquivo.name
            registrar_evento(
                "documento_veiculo.enviar",
                CategoriaAuditoria.OPERACAO,
                objeto=documento,
                depois=retrato(documento),
                regra="VEI-08",
            )
    except Exception:
        if gravado:
            _apagar_crlv_orfao(gravado)
        raise
    return veiculo


def _preenchido_pelo_documento(lidos: list[str], corrigidos: list[str]) -> dict[str, Any]:
    """A marca do evento (CA-247-03, CA-421-05): os campos lidos e os corrigidos, sem valores."""
    if not lidos:
        return {}
    return {
        "preenchido_pelo_documento": {"tipo": "crlv", "campos": lidos, "corrigidos": corrigidos}
    }


def _apagar_crlv_orfao(nome: str) -> None:
    """B-02 da T-328: o cadastro voltou atrás e o PDF ficou sem registro. Sai pelo provedor (o
    armazenamento privado não apaga arquivo de negócio, ADR 0009), sem nunca trocar o erro
    original, que é o que a pessoa precisa ver."""
    try:
        arquivos.provedor().apagar(nome)
    except Exception:
        logger.exception("CRLV órfão não apagado (VEI-08)")


def validar_novo(dados: dict[str, Any]) -> list[dict[str, str]]:
    """IMP-02: as validações de `cadastrar`, sem gravar e sem o limite do plano (a importação
    o confere ao gravar). Devolve `[{campo, codigo, mensagem}]`, vazia quando cabe cadastrar.
    Placa e chassi, no formato ou repetidos na empresa em qualquer estado, saem com `VEI-01`."""
    erros: list[dict[str, str]] = []
    try:
        _limpar_cadastro(dados)
    except ErroDeValidacao as erro:
        for campo, mensagens in erro.campos.items():
            codigo = "VEI-01" if campo in ("placa", "chassi") else "validacao"
            erros += [{"campo": campo, "codigo": codigo, "mensagem": m} for m in mensagens]
    com_erro = {erro["campo"] for erro in erros}
    for campo, normalizar in (("placa", normalizar_placa), ("chassi", normalizar_chassi)):
        valor = normalizar(str(dados.get(campo) or ""))
        if campo in com_erro or not valor:
            continue
        try:
            _conferir_unicos(
                valor if campo == "placa" else None, valor if campo == "chassi" else None
            )
        except Conflito as conflito:
            erros.append({"campo": campo, "codigo": "VEI-01", "mensagem": conflito.mensagem})
    return erros


CAMPOS_EDITAVEIS = (
    "renavam",
    "marca",
    "modelo",
    "ano_fabricacao",
    "ano_modelo",
    "cor",
    "combustivel",
    "categoria_id",
    "capacidade_tanque_litros",
    "valor_compra_centavos",
    "data_compra",
    "documento",
    "rastreador",
    "anotacoes",
)
# Campo do model → chave da API no evento `veiculo.editar` (VEI-09: `documento.lotacao`).
CHAVE_NO_EVENTO = {campo: chave for chave, campo in CAMPOS_DA_VEI_09.items()}


def _lidos_no_editar(
    veiculo: Veiculo, leitura: str | None, usuario: Any
) -> tuple[list[str], list[str]]:
    """Com o comprovante da leitura no editar (T-421) deste veículo e desta pessoa, os campos
    lidos e os corrigidos, comparados com o que ficou gravado. Sem ele, nada (ADR 0026, item 8)."""
    conferido = comprovante_leitura.conferir_do_veiculo("crlv", leitura, usuario, veiculo.pk)
    if conferido is None:
        return [], []
    hash_do_arquivo, resumos = conferido
    gravados = {campo: getattr(veiculo, campo) for campo in CAMPOS_DO_CRLV}
    gravados |= {chave: getattr(veiculo, campo) for chave, campo in CAMPOS_DA_VEI_09.items()}
    return comprovante_leitura.campos_pelo_hash(resumos, hash_do_arquivo, gravados)


def motivo_de_nao_trocar_tipo(
    veiculo: Veiculo, blocos: dict[str, dict[str, Any]] | None = None
) -> str | None:
    """VEI-11: com locação aberta (o veículo `reservado` ou `alugado`, ou à espera da retirada,
    ou o novo de uma troca pedida, LOC-09), o tipo não muda; `None` quando muda. A frase vai na
    dica do campo travado e no 409 `tipo_com_locacao_aberta`."""
    if blocos is None:
        blocos = leituras.blocos("veiculos.Veiculo", veiculo)
    codigo = (blocos.get("reserva") or {}).get("codigo") or (blocos.get("locacao_atual") or {}).get(
        "codigo"
    )
    if codigo:
        return f"Este veículo está na {codigo}. Troque o tipo depois da devolução."
    if veiculo.status in (S.RESERVADO, S.ALUGADO):  # dado antigo, sem a locação que o prendeu
        return "Este veículo está numa locação aberta. Troque o tipo depois da devolução."
    return None


def editar(
    veiculo: Veiculo,
    dados: dict[str, Any],
    *,
    leitura: str | None = None,
    usuario: Any = None,
) -> Veiculo:
    """PATCH: placa, chassi, status, km e filial não mudam por aqui. A categoria nova vale para
    locações novas; a locação em andamento mantém o preço congelado (LOC-15).

    Os blocos da VEI-09 mudam por chave (`{"documento": {"lotacao": 1}}` só muda a lotação), e
    o evento leva as chaves pontuadas. Com o comprovante `leitura` da leitura no editar, o evento
    leva `preenchido_pelo_documento`, como no cadastro (T-421)."""
    entrada = {campo: dados[campo] for campo in CAMPOS_EDITAVEIS if campo in dados}
    erros: dict[str, list[str]] = {}
    limpos: dict[str, Any] = {}
    _validar_dados(entrada, veiculo.filial_id, erros, limpos)
    if "ano_fabricacao" in limpos or "ano_modelo" in limpos:
        fabricacao = limpos.get("ano_fabricacao", veiculo.ano_fabricacao)
        modelo = limpos.get("ano_modelo", veiculo.ano_modelo)
        if not fabricacao <= modelo <= fabricacao + 1:
            erros["ano_modelo"] = ["O ano do modelo é o de fabricação ou o seguinte."]
    if erros:
        raise ErroDeValidacao(erros)
    categoria_antes = veiculo.categoria
    nova = limpos.get("categoria")
    if nova is not None and nova.tipo_veiculo != categoria_antes.tipo_veiculo:
        motivo = motivo_de_nao_trocar_tipo(veiculo)
        if motivo:
            raise Conflito("tipo_com_locacao_aberta", motivo)
    with transaction.atomic():
        antes = retrato(Veiculo._base_manager.get(pk=veiculo.pk))
        for campo, valor in limpos.items():
            setattr(veiculo, campo, valor)
        veiculo.save()
        mudou_antes, mudou_depois = diferenca(antes, retrato(veiculo))
        if "categoria_id" in mudou_depois:  # VEI-11: o nome e o tipo, para a auditoria se ler
            mudou_antes["categoria_nome"] = categoria_antes.nome
            mudou_depois["categoria_nome"] = veiculo.categoria.nome
            if veiculo.categoria.tipo_veiculo != categoria_antes.tipo_veiculo:
                mudou_antes["tipo_veiculo"] = categoria_antes.tipo_veiculo
                mudou_depois["tipo_veiculo"] = veiculo.categoria.tipo_veiculo
        lidos, corrigidos = _lidos_no_editar(veiculo, leitura, usuario)
        registrar_evento(
            "veiculo.editar",
            CategoriaAuditoria.OPERACAO,
            objeto=veiculo,
            antes={CHAVE_NO_EVENTO.get(c, c): v for c, v in mudou_antes.items()},
            depois={
                **{CHAVE_NO_EVENTO.get(c, c): v for c, v in mudou_depois.items()},
                **_preenchido_pelo_documento(lidos, corrigidos),
            },
        )
    return veiculo


def corrigir_identificacao(
    veiculo: Veiculo, motivo: str, placa: str | None = None, chassi: str | None = None
) -> Veiculo:
    """Erro de digitação na placa ou no chassi, só pelo administrador, com antes e depois."""
    texto = _exigir_motivo(motivo)
    erros: dict[str, list[str]] = {}
    limpos: dict[str, Any] = {}
    entrada = {k: v for k, v in (("placa", placa), ("chassi", chassi)) if v}
    if not entrada:
        erros["placa"] = ["Informe a placa ou o chassi corrigidos."]
    _validar_identificacao(entrada, erros, limpos)
    if erros:
        raise ErroDeValidacao(erros)
    with transaction.atomic():
        _conferir_unicos(limpos.get("placa"), limpos.get("chassi"), exceto=veiculo.pk)
        with auditar(
            veiculo,
            "veiculo.corrigir_identificacao",
            CategoriaAuditoria.OPERACAO,
            motivo=texto,
            regra="VEI-01",
        ):
            for campo, valor in limpos.items():
                setattr(veiculo, campo, valor)
            veiculo.save(update_fields=[*limpos, "atualizado_em"])
    return veiculo


def receber_na_troca(chassi: str, dados: dict[str, Any]) -> Veiculo:
    """Venda com troca (VEN-05, VEI-07). O chassi de um veículo `vendido` reaproveita o mesmo
    cadastro e o histórico, indo para `indisponivel` até a vistoria; chassi novo cria o
    veículo já `indisponivel` (`dados` como no cadastro, sem o chassi)."""
    chassi = normalizar_chassi(chassi)
    origem = OrigemDaMudanca(
        Origem.VENDA, dados.get("venda_id"), str(dados.get("venda_codigo") or "")
    )
    existente = Veiculo.objects.filter(chassi=chassi).first()
    if existente is not None:
        return transicionar(
            existente,
            S.INDISPONIVEL,
            origem=origem,
            motivo="Recebido numa troca",
            acao="receber_na_troca",
        )
    cadastro = {
        chave: valor
        for chave, valor in dados.items()
        if chave not in ("venda_id", "venda_codigo", "chassi")
    }
    limpos = _limpar_cadastro({**cadastro, "chassi": chassi})
    with transaction.atomic():
        _conferir_unicos(limpos["placa"], limpos["chassi"])
        return _criar(limpos, S.INDISPONIVEL, origem)


# --- Transferência (VEI-04, FIL-05) ---


def categoria_no_destino(veiculo: Veiculo, destino: Filial, categoria_id: int | None) -> Categoria:
    """VEI-04, FIL-04: categoria só da filial de origem pede a categoria no destino (ativa, do
    mesmo tipo, da empresa ou do destino). Categoria da empresa passa direto e continua; com
    `categoria_id` válido, o veículo vai para ela."""
    atual = veiculo.categoria
    if categoria_id is None:
        if atual.filial_id is None:
            return atual
        raise ErroDeValidacao(
            {
                "categoria_id": [
                    "A categoria atual é só desta filial. Escolha a categoria no destino."
                ]
            }
        )
    erros: dict[str, list[str]] = {}
    categoria = _categoria_para(categoria_id, destino.pk, erros)
    if categoria is None or categoria.tipo_veiculo != atual.tipo_veiculo:
        raise ErroDeValidacao(
            {
                "categoria_id": [
                    "Escolha uma categoria ativa do mesmo tipo, da empresa ou da filial de destino."
                ]
            }
        )
    return categoria


def transferir(
    veiculo: Veiculo,
    filial_destino_id: int,
    motivo: str = "",
    categoria_id: int | None = None,
    *,
    origem: OrigemDaMudanca = MANUAL,
) -> Veiculo:
    """Só `disponivel` (VEI-04), então nenhuma locação aberta muda de preço: a categoria nova
    vale a partir da próxima locação (LOC-01). Pela chegada da movimentação (origem
    `movimentacao`, MOV-06), também `indisponivel`, `em_manutencao` e `a_venda` (ADR 0028)."""
    pela_movimentacao = origem.tipo == Origem.MOVIMENTACAO
    with transaction.atomic():
        travado = _travar(veiculo)
        destino = Filial.ativos.filter(pk=filial_destino_id).first()
        if destino is None or destino.pk == travado.filial_id:
            raise ErroDeValidacao(
                {"filial_destino_id": ["Escolha outra filial ativa como destino."]}
            )
        aceitos = MOVIMENTAVEIS if pela_movimentacao else {S.DISPONIVEL}
        if travado.status not in aceitos:
            raise Conflito("VEI-04", "Só é possível transferir um veículo disponível")
        categoria = categoria_no_destino(travado, destino, categoria_id)
        origem_id, categoria_origem_id = travado.filial_id, travado.categoria_id
        with auditar(
            travado,
            "veiculo.transferir",
            CategoriaAuditoria.OPERACAO,
            motivo=motivo.strip(),
            regra="VEI-04",
        ):
            travado.filial = destino
            travado.categoria = categoria
            travado.save(update_fields=["filial", "categoria", "atualizado_em"])
        TransferenciaVeiculo.objects.create(
            veiculo=travado,
            filial_origem_id=origem_id,
            filial_destino=destino,
            categoria_origem_id=categoria_origem_id,
            categoria_destino=categoria,
            em=relogio.agora(),
            por_id=_quem(),
            motivo=motivo.strip()[:200],
        )
    _recarregar(veiculo)
    return veiculo


# --- Km (VEI-01, VEI-02) ---


def km_menor(km_atual: int) -> ErroDeRegra:
    return ErroDeRegra(
        "VEI-01",
        f"O km informado é menor que o atual ({formatar_km(km_atual)}). "
        "Para corrigir, use Corrigir km.",
        {"km_atual": km_atual},
    )


def _gravar_km(
    veiculo: Veiculo,
    km: int,
    origem: OrigemDaMudanca,
    *,
    correcao: bool = False,
    motivo: str = "",
) -> None:
    agora = relogio.agora()
    veiculo.km_atual = km
    veiculo.km_atualizado_em = agora
    veiculo.save(update_fields=["km_atual", "km_atualizado_em", "atualizado_em"])
    LeituraKm.objects.create(
        veiculo=veiculo,
        km=km,
        lido_em=agora,
        correcao=correcao,
        motivo=motivo[:200],
        por_id=_quem(),
        **_origem(origem),
    )
    # Recálculo das preventivas (MAN-03), assinado pelo app manutencao.
    publicar("veiculos.km_atualizado", veiculo_id=veiculo.pk, km=km)


def atualizar_km(veiculo: Veiculo, km: int, *, origem: OrigemDaMudanca = MANUAL) -> Veiculo:
    """Leitura avulsa, vistoria e OS (VEI-02). Km menor que o atual: 422 `VEI-01`."""
    if km < 0:
        raise ErroDeValidacao({"km": ["O km não pode ser negativo."]})
    with transaction.atomic():
        travado = _travar(veiculo)
        if travado.status == S.EM_MOVIMENTACAO and origem.tipo != Origem.MOVIMENTACAO:
            raise Conflito("MOV-05", "O km do veículo em movimentação entra na chegada.")
        if km < travado.km_atual:
            raise km_menor(travado.km_atual)
        _gravar_km(travado, km, origem)
    _recarregar(veiculo)
    return veiculo


def corrigir_km(
    veiculo: Veiculo, km: int, motivo: str, *, origem: OrigemDaMudanca = MANUAL
) -> Veiculo:
    """Correção pelo gerente ou administrador, na hora, com leitura de correção e auditoria
    (VEI-01). O vistoriador pede por `pedir_correcao_km` (APR-06)."""
    texto = _exigir_motivo(motivo)
    if km < 0:
        raise ErroDeValidacao({"km": ["O km não pode ser negativo."]})
    with transaction.atomic():
        travado = _travar(veiculo)
        with auditar(
            travado,
            "veiculo.corrigir_km",
            CategoriaAuditoria.OPERACAO,
            motivo=texto,
            regra="VEI-01",
        ):
            _gravar_km(travado, km, origem, correcao=True, motivo=texto)
    _recarregar(veiculo)
    return veiculo


def pedir_correcao_km(veiculo: Veiculo, km: int, motivo: str, solicitante: Any) -> Any:
    """Vistoriador: a correção para baixo vira o pedido APR-06 (ADR 0019), e o km fica como
    está até o gerente aprovar. Pedido igual ainda pendente: 409 `pedido_pendente`."""
    texto = _exigir_motivo(motivo)
    with transaction.atomic():
        travado = _travar(veiculo)
        if km >= travado.km_atual:
            raise ErroDeValidacao(
                {"km": ["O km informado não é menor que o atual. Use Registrar km."]}
            )
        return aprovacoes.pedir(
            tipo="APR-06",
            origem_tipo="veiculo",
            origem_id=travado.pk,
            origem_codigo=travado.placa,
            filial_id=travado.filial_id,
            solicitante=solicitante,
            titulo="Correção de km para baixo",
            detalhe=(
                f"{placa_com_hifen(travado.placa)} · {formatar_km(travado.km_atual)} → "
                f"{formatar_km(km)} km"
                f" · {texto}"
            ),
            motivo=texto,
            dados={"km_novo": km, "km_anterior": travado.km_atual},
            resumo=aprovacoes.Resumo(  # T-201, "Resumo por tipo"
                [
                    ("Km atual", f"{formatar_km(travado.km_atual)} km"),
                    ("Km pedido", f"{formatar_km(km)} km"),
                    ("Diferença", f"−{formatar_km(travado.km_atual - km)} km"),
                ]
            ),
        )


def aplicar_correcao_aprovada(
    veiculo_id: int, km_novo: int, km_anterior: int, motivo: str, pedido_id: int
) -> Veiculo:
    """O gerente aprovou o pedido APR-06 (assinante de `aprovacoes.pedido_decidido`): corrige o
    km como na correção direta, com a aprovação como origem da leitura.

    Se o km mudou depois do pedido (outra leitura entrou), a correção pedida não vale mais:
    409 `km_mudou`, e a aprovação volta inteira."""
    with transaction.atomic():
        travado = _travar(Veiculo.objects.get(pk=veiculo_id))
        if travado.km_atual != km_anterior:
            raise Conflito(
                "km_mudou",
                f"O km do veículo mudou depois do pedido ({formatar_km(km_anterior)} → "
                f"{formatar_km(travado.km_atual)}). Recuse e peça a correção de novo.",
                {"km_anterior": km_anterior, "km_atual": travado.km_atual},
            )
        origem = OrigemDaMudanca(Origem.APROVACAO, pedido_id, "")
        return corrigir_km(travado, km_novo, motivo or "Correção aprovada", origem=origem)


# --- Documentos (VEI-03, AUT-06, AUD-05) ---

DIAS_DO_ALERTA = 30  # VEI-03
# VEI-03: no dia do vencimento, estes não mudam de status; os gerentes recebem tarefa urgente.
EM_USO_NO_VENCIMENTO = {
    S.ALUGADO: "alugado",
    S.RESERVADO: "reservado",
    S.EM_MANUTENCAO: "em manutenção",
    S.EM_MOVIMENTACAO: "em movimentação",  # a chegada decide (MOV-05)
}


class SituacaoDocumento:
    EM_DIA = "em_dia"
    VENCE_EM_BREVE = "vence_em_breve"
    VENCIDO = "vencido"


def situacao_do_documento(validade: date, hoje: date) -> tuple[str, int | None]:
    """`(situacao, dias_para_vencer)`. No dia da validade o documento já conta como vencido,
    porque é o dia em que o veículo sai da frota (VEI-03)."""
    dias = (validade - hoje).days
    if dias <= 0:
        return SituacaoDocumento.VENCIDO, None
    if dias <= DIAS_DO_ALERTA:
        return SituacaoDocumento.VENCE_EM_BREVE, dias
    return SituacaoDocumento.EM_DIA, dias


def _nome_no_texto(tipo: str) -> str:
    """ "CRLV" fica em maiúsculas; os outros, em minúsculas no meio da frase."""
    rotulo = str(TipoDocumento(tipo).label)
    return rotulo if tipo == TipoDocumento.CRLV else rotulo.lower()


def documento_vencido(tipos: list[str], antes: str = "de desbloquear o veículo") -> ErroDeRegra:
    """`antes`: o que espera a renovação ("da retirada" na vistoria de saída)."""
    nomes = [_nome_no_texto(t) for t in tipos]
    lista = nomes[0] if len(nomes) == 1 else f"{', '.join(nomes[:-1])} e {nomes[-1]}"
    plural = "vencidos" if len(nomes) > 1 else "vencido"
    return ErroDeRegra(
        "VEI-03",
        f"Renove o {lista} {plural} antes {antes}.",
        {"documentos": tipos},
    )


def documentos_vencidos_que_bloqueiam(veiculo: Veiculo, hoje: date) -> list[str]:
    return sorted(
        DocumentoVeiculo.ativos.filter(
            veiculo=veiculo, tipo__in=DOCUMENTOS_QUE_BLOQUEIAM, validade__lte=hoje
        ).values_list("tipo", flat=True)
    )


def enviar_documento(
    veiculo: Veiculo,
    tipo: str,
    validade: date,
    arquivo: Any | None = None,
    exercicio: int | None = None,
) -> DocumentoVeiculo:
    """Novo documento; o ativo do mesmo tipo fica inativo (renovação). Renovar não muda o
    status: o veículo `indisponivel` volta pela ação `desbloquear` (VEI-03)."""
    if arquivo is not None:
        arquivos.validar(arquivo)
    with transaction.atomic():
        travado = _travar(veiculo)
        for anterior in DocumentoVeiculo.ativos.select_for_update().filter(
            veiculo=travado, tipo=tipo
        ):
            with auditar(anterior, "documento_veiculo.substituir", CategoriaAuditoria.OPERACAO):
                anterior.ativo = False
                anterior.save(update_fields=["ativo", "atualizado_em"])
        documento = DocumentoVeiculo.objects.create(
            veiculo=travado,
            tipo=tipo,
            validade=validade,
            exercicio=exercicio if tipo == TipoDocumento.CRLV else None,
            arquivo_nome=(arquivo.name if arquivo is not None else "")[:120],
            por_id=_quem(),
        )
        if arquivo is not None:
            documento.arquivo.save(arquivo.name, arquivo, save=True)
        registrar_evento(
            "documento_veiculo.enviar",
            CategoriaAuditoria.OPERACAO,
            objeto=documento,
            depois=retrato(documento),
            regra="VEI-03",
        )
    return documento


def _link_do_veiculo(veiculo: Veiculo) -> str:
    return f"/veiculos/{veiculo.pk}"


def _gerentes(veiculo: Veiculo) -> list[int]:
    """FIL-02: avisos e tarefas para o gerente vão a todos os gerentes da filial."""
    return [g["id"] for g in filiais_selectors.gerentes(veiculo.filial)]


def aplicar_vencimento_de_documentos(hoje: date) -> dict[str, int]:
    """AUT-06 (VEI-03), uma vez por dia. Rodar de novo no mesmo dia não repete nada.

    - 30 dias antes: alerta aos gerentes da filial, uma vez por documento.
    - No dia, CRLV ou seguro: veículo `disponivel` vai para `indisponivel`; `alugado`, `reservado`
      e `em_manutencao` não mudam, e os gerentes recebem uma tarefa urgente. IPVA e rastreador não
      mudam o status nem geram tarefa.
    """
    contagem = {"alertas": 0, "indisponiveis": 0, "tarefas": 0}
    ativos = DocumentoVeiculo.ativos.select_related("veiculo", "veiculo__filial")

    a_vencer = ativos.filter(
        validade__gt=hoje,
        validade__lte=hoje + timedelta(days=DIAS_DO_ALERTA),
        alerta_enviado_em__isnull=True,
    )
    for documento in a_vencer:
        veiculo = documento.veiculo
        with transaction.atomic():
            contagem["alertas"] += avisar(
                _gerentes(veiculo),
                tipo="documento_vencendo",
                titulo=(
                    f"{TipoDocumento(documento.tipo).label} da {placa_com_hifen(veiculo.placa)} "
                    "vence em "
                    f"{documento.validade:%d/%m/%Y}"
                ),
                link=_link_do_veiculo(veiculo),
                chave=f"aut06-alerta-{documento.pk}",
            )
            documento.alerta_enviado_em = relogio.agora()
            documento.save(update_fields=["alerta_enviado_em", "atualizado_em"])
            publicar(
                "veiculos.documento_vencendo",
                documento_id=documento.pk,
                veiculo_id=veiculo.pk,
                tipo=documento.tipo,
                validade=documento.validade.isoformat(),
            )

    vencidos = ativos.filter(tipo__in=DOCUMENTOS_QUE_BLOQUEIAM, validade__lte=hoje)
    for documento in vencidos:
        veiculo = documento.veiculo
        rotulo = TipoDocumento(documento.tipo).label
        if veiculo.status == S.DISPONIVEL:
            transicionar(
                veiculo,
                S.INDISPONIVEL,
                origem=OrigemDaMudanca(Origem.DOCUMENTO, documento.pk, ""),
                motivo=f"{rotulo} vencido",
                acao="documento_vencido",
            )
            contagem["indisponiveis"] += 1
        elif veiculo.status in EM_USO_NO_VENCIMENTO:
            contagem["tarefas"] += avisar(
                _gerentes(veiculo),
                tipo=f"documento_vencido_{veiculo.status}",
                titulo=(
                    f"{rotulo} da {placa_com_hifen(veiculo.placa)} venceu com o veículo "
                    f"{EM_USO_NO_VENCIMENTO[S(veiculo.status)]}. Regularize o documento."
                ),
                link=_link_do_veiculo(veiculo),
                urgente=True,
                chave=f"aut06-vencido-{documento.pk}",
            )
    return contagem


# --- Categorias e preços (LOC-01, LOC-15) ---


def _nome_em_uso(nome: str, filial_id: int | None, exceto: int | None = None) -> None:
    existentes = Categoria.objects.annotate(minusculo=Lower("nome")).filter(minusculo=nome.lower())
    if filial_id is None:
        existentes = existentes.filter(filial__isnull=True)
    else:
        existentes = existentes.filter(filial_id=filial_id)
    if exceto is not None:
        existentes = existentes.exclude(pk=exceto)
    if existentes.exists():
        raise Conflito("categoria_nome_em_uso", "Já existe uma categoria com esse nome")


def tem_veiculos(categoria: Categoria) -> bool:
    return bool(categoria.veiculos.exclude(status__in=FORA_DA_FROTA).exists())


def categoria_com_veiculos(acao: str) -> ErroDeRegra:
    return ErroDeRegra(
        "categoria_com_veiculos",
        f"Esta categoria ainda tem veículos. Mude os veículos de categoria antes de {acao}.",
    )


def _validar_categoria(dados: dict[str, Any]) -> dict[str, Any]:
    erros: dict[str, list[str]] = {}
    limpos: dict[str, Any] = {}
    if "nome" in dados:
        limpos["nome"] = str(dados["nome"] or "").strip()
        if not limpos["nome"]:
            erros["nome"] = ["Informe o nome da categoria."]
    if "tipo_veiculo" in dados:
        limpos["tipo_veiculo"] = dados["tipo_veiculo"]
        if dados["tipo_veiculo"] not in TipoVeiculo.values:
            erros["tipo_veiculo"] = ["Escolha moto ou carro."]
    if "filial_id" in dados:
        limpos["filial_id"] = dados["filial_id"]
        if (
            dados["filial_id"] is not None
            and not Filial.ativos.filter(pk=dados["filial_id"]).exists()
        ):
            erros["filial_id"] = ["Escolha uma filial ativa."]
    if erros:
        raise ErroDeValidacao(erros)
    return limpos


CAMPOS_DO_PRECO = ("diaria_centavos", "semanal_centavos", "mensal_centavos", "caucao_centavos")
CAMPOS_DO_PLANO = ("diaria_centavos", "semanal_centavos", "mensal_centavos")  # sem a caução


def criar_categoria(dados: dict[str, Any], preco: dict[str, Any]) -> Categoria:
    limpos = _validar_categoria(dados)
    faltando = [c for c in ("nome", "tipo_veiculo") if c not in limpos]
    if faltando:
        raise ErroDeValidacao({campo: ["Campo obrigatório."] for campo in faltando})
    with transaction.atomic():
        _nome_em_uso(limpos["nome"], limpos.get("filial_id"))
        categoria = Categoria.objects.create(**limpos)
        registrar_evento(
            "categoria.criar",
            CategoriaAuditoria.CONFIGURACOES,
            objeto=categoria,
            depois=retrato(categoria),
            regra="LOC-01",
        )
        _gravar_preco(categoria, relogio.hoje(), preco)
    return categoria


def editar_categoria(categoria: Categoria, dados: dict[str, Any]) -> Categoria:
    """`tipo_veiculo` define a CNH exigida (CLI-02) e não muda com veículos na categoria; a
    filial também não, para o veículo não ficar com categoria de outra filial."""
    limpos = _validar_categoria(dados)
    with transaction.atomic():
        mudou_tipo = limpos.get("tipo_veiculo", categoria.tipo_veiculo) != categoria.tipo_veiculo
        mudou_filial = "filial_id" in limpos and limpos["filial_id"] != categoria.filial_id
        if (mudou_tipo or mudou_filial) and tem_veiculos(categoria):
            raise categoria_com_veiculos("mudar o tipo ou a filial")
        _nome_em_uso(
            limpos.get("nome", categoria.nome),
            limpos.get("filial_id", categoria.filial_id),
            exceto=categoria.pk,
        )
        with auditar(categoria, "categoria.editar", CategoriaAuditoria.CONFIGURACOES):
            for campo, valor in limpos.items():
                setattr(categoria, campo, valor)
            categoria.save()
    return categoria


def desativar_categoria(categoria: Categoria) -> Categoria:
    """Some da escolha em cadastros novos. 422 `categoria_com_veiculos` com veículos ativos."""
    with transaction.atomic():
        if not categoria.ativo:
            return categoria
        if tem_veiculos(categoria):
            raise categoria_com_veiculos("desativar")
        with auditar(categoria, "categoria.desativar", CategoriaAuditoria.CONFIGURACOES):
            categoria.ativo = False
            categoria.save(update_fields=["ativo", "atualizado_em"])
    return categoria


def reativar_categoria(categoria: Categoria) -> Categoria:
    with transaction.atomic():
        if categoria.ativo:
            return categoria
        _nome_em_uso(categoria.nome, categoria.filial_id, exceto=categoria.pk)
        with auditar(categoria, "categoria.reativar", CategoriaAuditoria.CONFIGURACOES):
            categoria.ativo = True
            categoria.save(update_fields=["ativo", "atualizado_em"])
    return categoria


def _validar_preco(preco: dict[str, Any]) -> dict[str, int]:
    erros = {
        campo: ["Informe o valor."]
        for campo in CAMPOS_DO_PRECO
        if not isinstance(preco.get(campo), int) or preco[campo] < 0
    }
    if erros:
        raise ErroDeValidacao(erros)
    return {campo: int(preco[campo]) for campo in CAMPOS_DO_PRECO}


def _gravar_preco(categoria: Categoria, vigente_desde: date, preco: dict[str, Any]) -> Any:
    valores = _validar_preco(preco)
    # T-201: `antes` é o preço que valia na véspera, só nos valores que mudam (sem ele, categoria
    # nova); o texto pronto sai do formatador de `veiculos` (`textos.py`).
    anterior = (
        categoria.precos.filter(vigente_desde__lt=vigente_desde).order_by("-vigente_desde").first()
    )
    antes = (
        {c: getattr(anterior, c) for c in CAMPOS_DO_PRECO if getattr(anterior, c) != valores[c]}
        if anterior is not None
        else {}
    )
    novo = PrecoCategoria.objects.create(
        categoria=categoria, vigente_desde=vigente_desde, alterado_por_id=_quem(), **valores
    )
    registrar_evento(
        "categoria.definir_preco",
        CategoriaAuditoria.CONFIGURACOES,
        objeto=categoria,
        antes=antes,
        depois={"vigente_desde": vigente_desde.isoformat(), **valores},
        regra="LOC-15",
    )
    # IMP-07: o preço que já vale hoje marca o passo `precos`; o agendado, na leitura da data.
    if (
        categoria.ativo
        and vigente_desde <= relogio.hoje()
        and any(valores[c] > 0 for c in CAMPOS_DO_PLANO)
    ):
        registrar_passo_implantacao("precos")
    return novo


def locacoes_em_andamento(categoria: Categoria) -> int:
    """Fornecido pelo app `locacoes` (ADR 0015); 0 enquanto ele não existe."""
    return leituras.contar(ALVO_CATEGORIA, categoria.pk, ["locacoes_em_andamento"])[
        "locacoes_em_andamento"
    ]


def criar_preco(
    categoria: Categoria, preco: dict[str, Any], vigente_desde: date | None = None
) -> PrecoCategoria:
    """Preço novo a partir de hoje ou de uma data futura (LOC-15): o passado não se reescreve,
    e o contrato já assinado mantém o preço da assinatura."""
    data = vigente_desde or relogio.hoje()
    with transaction.atomic():
        Categoria.objects.select_for_update().get(pk=categoria.pk)
        if categoria.precos.filter(vigente_desde=data).exists():
            raise Conflito("preco_ja_definido", "Já existe preço a partir desta data")
        if data < relogio.hoje():
            raise ErroDeValidacao(
                {"vigente_desde": ["O preço vale a partir de hoje ou de uma data futura."]}
            )
        return _gravar_preco(categoria, data, preco)  # type: ignore[no-any-return]


def trocar_preco_futuro(preco: PrecoCategoria, valores: dict[str, Any]) -> PrecoCategoria:
    """PUT de um preço agendado, até a data chegar."""
    limpos = _validar_preco(valores)
    with transaction.atomic():
        preco = PrecoCategoria.objects.select_for_update().get(pk=preco.pk)
        if preco.vigente_desde <= relogio.hoje():
            raise Conflito(
                "preco_ja_vigente",
                "Este preço já está valendo. Crie um preço novo a partir de hoje.",
            )
        with auditar(
            preco.categoria,
            "categoria.trocar_preco_agendado",
            CategoriaAuditoria.CONFIGURACOES,
            regra="LOC-15",
        ):
            for campo, valor in limpos.items():
                setattr(preco, campo, valor)
            preco.alterado_por_id = _quem()
            preco.save()
    return preco


# --- Extras (LOC-02) ---


def _validar_extra(dados: dict[str, Any], parcial: bool) -> dict[str, Any]:
    erros: dict[str, list[str]] = {}
    limpos: dict[str, Any] = {}
    if "nome" in dados:
        limpos["nome"] = str(dados["nome"] or "").strip()
        if not limpos["nome"]:
            erros["nome"] = ["Informe o nome do extra."]
    if "valor_centavos" in dados:
        limpos["valor_centavos"] = dados["valor_centavos"]
    if "cobranca" in dados:
        limpos["cobranca"] = dados["cobranca"]
        if dados["cobranca"] not in Extra.Cobranca.values:
            erros["cobranca"] = ["Escolha por período ou única."]
    if not parcial:
        for campo in ("nome", "valor_centavos", "cobranca"):
            if campo not in dados:
                erros[campo] = ["Campo obrigatório."]
    if erros:
        raise ErroDeValidacao(erros)
    return limpos


def criar_extra(dados: dict[str, Any]) -> Extra:
    limpos = _validar_extra(dados, parcial=False)
    with transaction.atomic():
        extra = Extra.objects.create(**limpos)
        registrar_evento(
            "extra.criar",
            CategoriaAuditoria.CONFIGURACOES,
            objeto=extra,
            depois=retrato(extra),
            regra="LOC-02",
        )
    return extra


def editar_extra(extra: Extra, dados: dict[str, Any]) -> Extra:
    """O valor novo vale para locações novas: a locação copia o valor quando é criada."""
    limpos = _validar_extra(dados, parcial=True)
    with transaction.atomic(), auditar(extra, "extra.editar", CategoriaAuditoria.CONFIGURACOES):
        for campo, valor in limpos.items():
            setattr(extra, campo, valor)
        extra.save()
    return extra


def desativar_extra(extra: Extra) -> Extra:
    with transaction.atomic(), auditar(extra, "extra.desativar", CategoriaAuditoria.CONFIGURACOES):
        extra.ativo = False
        extra.save(update_fields=["ativo", "atualizado_em"])
    return extra


# --- Galeria do veículo (VEI-10, ADR 0036) ---

MENSAGEM_DA_FOTO = "Envie uma foto JPG ou PNG de até 10 MB."
MENSAGEM_DO_LIMITE = "O veículo já tem 20 fotos. Apague uma para enviar outra."
GALERIA_SO_PARA_VER = {
    S.VENDIDO: "A galeria de veículo vendido fica só para ver.",
    S.BAIXADO: "A galeria de veículo baixado fica só para ver.",
}


def motivo_da_galeria_so_para_ver(veiculo: Veiculo) -> str | None:
    """Vendido e baixado: a galeria só se vê (VEI-10). `None` nos outros estados."""
    return GALERIA_SO_PARA_VER.get(S(veiculo.status))


def _exigir_galeria_editavel(veiculo: Veiculo) -> None:
    motivo = motivo_da_galeria_so_para_ver(veiculo)
    if motivo:
        raise Conflito("VEI-10", motivo)


def _foto_limpa(arquivo: Any) -> tuple[Any, str]:
    """JPG ou PNG pelo conteúdo, até 10 MB, reprocessada sem EXIF nem GPS (AUD-05). Toda recusa
    sai com a mensagem da VEI-10, e não com as de `comum.arquivos` (ADR 0036, item 2)."""
    if arquivo is None:
        raise ErroDeValidacao({"arquivo": [MENSAGEM_DA_FOTO]})
    try:
        formato = arquivos.validar(arquivo)
        if formato.extensao == "pdf":
            raise ErroDeValidacao({"arquivo": [MENSAGEM_DA_FOTO]})
        limpo = arquivos.sem_metadados(arquivo, formato)
    except ErroDeValidacao:
        raise ErroDeValidacao({"arquivo": [MENSAGEM_DA_FOTO]}) from None
    return limpo, formato.extensao


def _numero(veiculo: Veiculo, foto: FotoVeiculo) -> int:
    """A posição na exibição (capa primeiro, depois a ordem de envio), de 1 em diante."""
    ids = list(
        FotoVeiculo.ativos.filter(veiculo=veiculo)
        .order_by("-capa", "ordem", "id")
        .values_list("pk", flat=True)
    )
    return ids.index(foto.pk) + 1


def _foto_ativa(veiculo: Veiculo, foto_id: int, travar_foto: bool = False) -> FotoVeiculo:
    fotos = FotoVeiculo.ativos.filter(veiculo=veiculo, pk=foto_id)
    if travar_foto:
        fotos = fotos.select_for_update()
    foto: FotoVeiculo | None = fotos.first()
    if foto is None:
        raise NaoEncontrado("nao_encontrado", "Foto não encontrada.")
    return foto


def _nova_foto(veiculo: Veiculo, limpo: Any, formato: str, ordem: int, capa: bool) -> FotoVeiculo:
    foto = FotoVeiculo.objects.create(
        veiculo=veiculo,
        formato=formato,
        ordem=ordem,
        capa=capa,
        enviada_por_id=_quem(),
        enviada_em=relogio.agora(),
    )
    # A linha antes do arquivo: o caminho leva o id (ADR 0009).
    foto.arquivo.save(limpo.name, limpo, save=True)
    return foto


def _evento_da_galeria(acao: str, veiculo: Veiculo, detalhes: dict[str, Any]) -> None:
    """Evento do veículo, sem a imagem (AUD-01)."""
    registrar_evento(
        acao, CategoriaAuditoria.OPERACAO, objeto=veiculo, depois=detalhes, regra="VEI-10"
    )


def enviar_foto(veiculo: Veiculo, arquivo: Any) -> FotoVeiculo:
    """Uma foto por chamada (ADR 0036, item 3). O status vem antes do arquivo; o limite de 20,
    com o veículo travado. A primeira ativa vira capa; a nova entra no fim da ordem."""
    _exigir_galeria_editavel(veiculo)
    limpo, formato = _foto_limpa(arquivo)
    with transaction.atomic():
        travado = travar(veiculo)
        _exigir_galeria_editavel(travado)
        ativas = FotoVeiculo.ativos.filter(veiculo=travado)
        if ativas.count() >= LIMITE_DA_GALERIA:
            raise ErroDeValidacao({"arquivo": [MENSAGEM_DO_LIMITE]})
        maior = FotoVeiculo.objects.filter(veiculo=travado).aggregate(maior=Max("ordem"))["maior"]
        capa = not ativas.filter(capa=True).exists()
        foto = _nova_foto(travado, limpo, formato, (maior or 0) + 1, capa)
        _evento_da_galeria(
            "veiculo.foto_enviar",
            travado,
            {"foto_id": foto.pk, "numero": _numero(travado, foto), "capa": capa},
        )
    return foto


def trocar_foto(veiculo: Veiculo, foto_id: int, arquivo: Any) -> FotoVeiculo:
    """A nova fica na posição e com a capa da antiga, que fica inativa e guardada, ligada à nova
    (`substituida_por`). O total não muda, e o limite não se aplica."""
    _exigir_galeria_editavel(veiculo)
    _foto_ativa(veiculo, foto_id)
    limpo, formato = _foto_limpa(arquivo)
    with transaction.atomic():
        travado = travar(veiculo)
        _exigir_galeria_editavel(travado)
        antiga = _foto_ativa(travado, foto_id, travar_foto=True)
        # A antiga sai antes de a nova entrar: os únicos parciais de capa e de ordem valem já.
        antiga.ativo = False
        antiga.save(update_fields=["ativo", "atualizado_em"])
        nova = _nova_foto(travado, limpo, formato, antiga.ordem, antiga.capa)
        antiga.substituida_por = nova
        antiga.save(update_fields=["substituida_por", "atualizado_em"])
        _evento_da_galeria(
            "veiculo.foto_trocar", travado, {"foto_id_antiga": antiga.pk, "foto_id_nova": nova.pk}
        )
    return nova


def usar_como_capa(veiculo: Veiculo, foto_id: int) -> FotoVeiculo:
    """A escolhida vira capa e a anterior perde a marca, na mesma transação. Já capa: nada muda
    e não há evento."""
    _exigir_galeria_editavel(veiculo)
    with transaction.atomic():
        travado = travar(veiculo)
        _exigir_galeria_editavel(travado)
        foto = _foto_ativa(travado, foto_id, travar_foto=True)
        if foto.capa:
            return foto
        anterior = FotoVeiculo.ativos.select_for_update().filter(veiculo=travado, capa=True).first()
        if anterior is not None:
            anterior.capa = False
            anterior.save(update_fields=["capa", "atualizado_em"])
        foto.capa = True
        foto.save(update_fields=["capa", "atualizado_em"])
        _evento_da_galeria(
            "veiculo.foto_capa",
            travado,
            {"foto_id": foto.pk, "capa_anterior_id": anterior.pk if anterior else None},
        )
    return foto


def apagar_foto(veiculo: Veiculo, foto_id: int) -> FotoVeiculo:
    """Sai da galeria e da ficha e não volta: `ativo=False`, com o arquivo guardado e quem
    apagou. Apagada a capa, a ativa mais antiga (menor `ordem`) vira capa."""
    _exigir_galeria_editavel(veiculo)
    with transaction.atomic():
        travado = travar(veiculo)
        _exigir_galeria_editavel(travado)
        foto = _foto_ativa(travado, foto_id, travar_foto=True)
        era_capa = foto.capa
        foto.ativo = False
        foto.capa = False
        foto.apagada_por_id = _quem()
        foto.save(update_fields=["ativo", "capa", "apagada_por", "atualizado_em"])
        nova_capa = None
        if era_capa:
            nova_capa = (
                FotoVeiculo.ativos.select_for_update()
                .filter(veiculo=travado)
                .order_by("ordem", "id")
                .first()
            )
            if nova_capa is not None:
                nova_capa.capa = True
                nova_capa.save(update_fields=["capa", "atualizado_em"])
        _evento_da_galeria(
            "veiculo.foto_apagar",
            travado,
            {
                "foto_id": foto.pk,
                "era_capa": era_capa,
                "nova_capa_id": nova_capa.pk if nova_capa else None,
            },
        )
    return foto
