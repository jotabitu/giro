"""Regras das movimentações (MOV-01 a MOV-06, ADR 0028). Único lugar que grava neste app.

O veículo muda de status, de km e de filial só pelos serviços de `veiculos`; a despesa da
parada nasce por `financeiro.services.lancar_despesa`, com a origem `movimentacao`.
"""

import unicodedata
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from django.db import IntegrityError, transaction

from apps.contas import selectors as contas_selectors
from apps.filiais.models import Filial
from apps.financeiro import services as financeiro
from apps.financeiro.models import CategoriaDespesa
from apps.locacoes import selectors as locacoes_selectors
from apps.veiculos import services as veiculos
from apps.veiculos.models import (
    MOVIMENTAVEIS,
    Categoria,
    Origem,
    StatusVeiculo,
    TipoDocumento,
    Veiculo,
)
from comum import arquivos, estados, relogio
from comum.auditoria import Categoria as CategoriaAuditoria
from comum.auditoria import auditar, registrar_evento, retrato
from comum.erros import Conflito, ErroDeValidacao, SemPermissao
from comum.permissoes import filiais_permitidas

from .models import (
    ABERTAS,
    FotoChegadaMovimentacao,
    LocalApoio,
    Movimentacao,
    ParadaMovimentacao,
    PosicaoFoto,
    StatusMovimentacao,
    TipoLocal,
)

S = StatusMovimentacao
V = StatusVeiculo
GESTAO = frozenset({"administrador", "gerente"})
# O financeiro não leva (MOV-02, CA-246-11) nem recebe: a chegada tem vistoria rápida (T-302).
NAO_LEVAM = ("financeiro",)
NAO_RECEBEM = ("financeiro",)
POSICOES = tuple(PosicaoFoto.values)
SEM_PERMISSAO = "Seu perfil não tem acesso a esta ação."
VERBO = {
    S.EM_TRANSITO: "iniciar",
    S.CANCELADA: "cancelar",
    S.NO_LOCAL: "registrar a chegada na parada de",
    S.CONCLUIDA: "concluir",
}


def sem_permissao() -> SemPermissao:
    return SemPermissao("permissao", SEM_PERMISSAO)


def _transicao(de: str, para: str) -> Conflito:
    return Conflito(
        "transicao_movimentacao",
        f"Não é possível {VERBO.get(S(para), 'mudar')} uma movimentação {S(de).label.lower()}",
        {"de": de, "para": para},
    )


def _origem(movimentacao: Movimentacao) -> veiculos.OrigemDaMudanca:
    return veiculos.OrigemDaMudanca(Origem.MOVIMENTACAO, movimentacao.pk, movimentacao.codigo)


# --- Quem pode (MOV-02, USR-07) ---


def gere(usuario: Any, filial_id: int) -> bool:
    """Administrador, e gerente da filial (USR-07)."""
    return getattr(usuario, "perfil", "") in GESTAO and filial_id in filiais_permitidas(usuario)


def exigir_gestao(usuario: Any, filial_id: int) -> None:
    if not gere(usuario, filial_id):
        raise sem_permissao()


def registra_chegada(movimentacao: Movimentacao, usuario: Any) -> bool:
    """Quem leva, o gerente da filial de saída ou o administrador (MOV-02)."""
    return movimentacao.levado_por_id == getattr(usuario, "pk", None) or gere(
        usuario, movimentacao.filial_saida_id
    )


def exigir_chegada(movimentacao: Movimentacao, usuario: Any) -> None:
    if not registra_chegada(movimentacao, usuario):
        raise sem_permissao()


# --- Locais de apoio (MOV-01) ---


def nome_de_busca(nome: str) -> str:
    decomposto = unicodedata.normalize("NFKD", nome)
    sem_acento = "".join(c for c in decomposto if not unicodedata.combining(c))
    return " ".join(sem_acento.casefold().split())


def criar_local(nome: str, tipo: str) -> LocalApoio:
    """Nome único na empresa, sem diferença de maiúsculas, acentos e espaços (CA-246-15)."""
    nome = " ".join(nome.split())
    if not nome:
        raise ErroDeValidacao({"nome": ["Informe o nome do local."]})
    if tipo not in TipoLocal.values:
        raise ErroDeValidacao({"tipo": ["Escolha lava-jato, oficina, despachante ou outro."]})
    busca = nome_de_busca(nome)
    existente = LocalApoio.objects.filter(nome_busca=busca).first()
    if existente is not None:
        raise _local_existente(existente)
    try:
        with transaction.atomic():
            local = LocalApoio.objects.create(nome=nome[:80], nome_busca=busca[:80], tipo=tipo)
            registrar_evento(
                "local_apoio.criar",
                CategoriaAuditoria.OPERACAO,
                objeto=local,
                depois=retrato(local),
                regra="MOV-01",
            )
    except IntegrityError as erro:
        raise _local_existente(LocalApoio.objects.get(nome_busca=busca)) from erro
    return local


def _local_existente(local: LocalApoio) -> Conflito:
    return Conflito(
        "local_existente",
        "Já existe um local com este nome.",
        {"local_id": local.pk, "ativo": local.ativo},
    )


def ativar_local(local: LocalApoio, ativo: bool) -> LocalApoio:
    """Inativar e reativar (administrador). Nada é apagado; a movimentação antiga mantém o nome."""
    if local.ativo == ativo:
        return local
    acao = "local_apoio.reativar" if ativo else "local_apoio.inativar"
    with auditar(local, acao, CategoriaAuditoria.OPERACAO, regra="MOV-01"):
        local.ativo = ativo
        local.save(update_fields=["ativo", "atualizado_em"])
    return local


# --- Veículo (MOV-03) ---


def _motivo_do_veiculo(veiculo: Veiculo) -> Conflito | None:
    """Alugado, reservado, vendido, baixado, em movimentação, ou disponível com locação
    `aguardando_retirada` (CA-246-04, CA-246-19). Lido com a linha do veículo travada."""
    if veiculo.status == V.ALUGADO:
        locacao = locacoes_selectors.locacao_aberta(veiculo)
        return Conflito(
            "MOV-03",
            "Veículo alugado não se movimenta.",
            {"status": veiculo.status, "locacao_codigo": locacao.codigo if locacao else None},
        )
    if veiculo.status not in MOVIMENTAVEIS:
        return Conflito(
            "MOV-03",
            f"Veículo {V(veiculo.status).label.lower()} não se movimenta.",
            {"status": veiculo.status},
        )
    locacao = locacoes_selectors.locacao_aberta(veiculo)
    if locacao is not None:
        return Conflito(
            "MOV-03",
            f"O veículo está reservado na {locacao.codigo}.",
            {"status": veiculo.status, "locacao_codigo": locacao.codigo},
        )
    return None


def _ja_aberta(veiculo_id: int, exceto: int | None = None) -> Conflito | None:
    aberta = Movimentacao.objects.filter(veiculo_id=veiculo_id, status__in=ABERTAS)
    if exceto is not None:
        aberta = aberta.exclude(pk=exceto)
    existente = aberta.first()
    if existente is None:
        return None
    return Conflito(
        "MOV-03",
        f"O veículo já está na {existente.codigo}.",
        {"movimentacao_id": existente.pk},
    )


# --- Corpo da criação e da edição ---


def _pessoa_da_filial(
    usuario_id: Any, filial_id: int, campo: str, excluir: tuple[str, ...], mensagem: str
) -> Any:
    pessoas = {p.pk: p for p in contas_selectors.pessoas_da_filial(filial_id, excluir)}
    if not isinstance(usuario_id, int) or usuario_id not in pessoas:
        raise ErroDeValidacao({campo: [mensagem]})
    return pessoas[usuario_id]


def _paradas(dados: list[dict[str, Any]]) -> list[dict[str, Any]]:
    erros: dict[str, list[str]] = {}
    locais = LocalApoio.objects.in_bulk([p.get("local_id") for p in dados])
    limpas = []
    for indice, parada in enumerate(dados):
        local = locais.get(parada.get("local_id"))
        if local is None or not local.ativo:
            erros[f"paradas[{indice}].local_id"] = ["Escolha um local de apoio ativo."]
            continue
        servico = " ".join(str(parada.get("servico") or "").split())
        if not servico:
            erros[f"paradas[{indice}].servico"] = ["Informe o serviço."]
        padrao = CategoriaDespesa.MANUTENCAO if local.tipo == TipoLocal.OFICINA else "outros"
        categoria = parada.get("categoria") or padrao
        if categoria not in CategoriaDespesa.values:
            erros[f"paradas[{indice}].categoria"] = ["Escolha uma categoria de despesa."]
        limpas.append(
            {
                "ordem": indice + 1,
                "local": local,
                "servico": servico[:80],
                "categoria": categoria,
                "valor_previsto_centavos": int(parada.get("valor_previsto_centavos") or 0),
            }
        )
    if erros:
        raise ErroDeValidacao(erros)
    return limpas


def _categoria_destino(veiculo: Veiculo, destino: Filial, categoria_id: int | None) -> Categoria:
    """VEI-04: a categoria só da filial de saída pede a categoria no destino (CA-246-09)."""
    if categoria_id is None and veiculo.categoria.filial_id is not None:
        raise ErroDeValidacao(
            {"categoria_destino_id": [f"Escolha a categoria do veículo na {destino.nome}."]}
        )
    try:
        return veiculos.categoria_no_destino(veiculo, destino, categoria_id)
    except ErroDeValidacao as erro:
        raise ErroDeValidacao({"categoria_destino_id": next(iter(erro.campos.values()))}) from erro


def _destino_e_mais(veiculo: Veiculo, dados: dict[str, Any]) -> dict[str, Any]:
    destino = Filial.ativos.filter(pk=dados.get("destino_filial_id")).first()
    if destino is None:
        raise ErroDeValidacao({"destino_filial_id": ["Escolha uma filial ativa como destino."]})
    transferencia = destino.pk != veiculo.filial_id
    categoria = (
        _categoria_destino(veiculo, destino, dados.get("categoria_destino_id"))
        if transferencia
        else None
    )
    levado_por = _pessoa_da_filial(
        dados.get("levado_por_id"),
        veiculo.filial_id,
        "levado_por_id",
        NAO_LEVAM,
        "Escolha quem leva entre as pessoas da filial do veículo.",
    )
    return {
        "destino": destino,
        "categoria_destino": categoria,
        "levado_por": levado_por,
        # Na transferência a vistoria rápida é obrigatória (MOV-05).
        "vistoria_rapida": True if transferencia else bool(dados.get("vistoria_rapida")),
        "paradas": _paradas(list(dados.get("paradas") or [])),
    }


def _agendada_para(dados: dict[str, Any]) -> datetime:
    quando = dados.get("agendada_para")
    if quando is None:
        raise ErroDeValidacao({"agendada_para": ["Informe quando a movimentação sai."]})
    if quando <= relogio.agora():
        raise ErroDeValidacao({"agendada_para": ["Escolha um momento no futuro."]})
    return quando  # type: ignore[no-any-return]


def _gravar_paradas(movimentacao: Movimentacao, paradas: list[dict[str, Any]]) -> None:
    for parada in paradas:
        ParadaMovimentacao.objects.create(movimentacao=movimentacao, **parada)


# --- Criar, editar, iniciar, cancelar ---


def criar(dados: dict[str, Any], usuario: Any) -> Movimentacao:
    """`sair_agora` nasce `em_transito` com os efeitos de Iniciar; senão, `agendada` (MOV-01 a
    MOV-03, MOV-06)."""
    veiculo = Veiculo.objects.select_related("categoria").filter(pk=dados.get("veiculo_id")).first()
    if veiculo is None or veiculo.filial_id not in filiais_permitidas(usuario):
        raise ErroDeValidacao({"veiculo_id": ["Veículo não encontrado."]})
    exigir_gestao(usuario, veiculo.filial_id)
    campos = _destino_e_mais(veiculo, dados)
    sair_agora = bool(dados.get("sair_agora"))
    agendada_para = None if sair_agora else _agendada_para(dados)
    paradas = campos.pop("paradas")
    try:
        with transaction.atomic():
            travado = veiculos.travar(veiculo)
            erro = _ja_aberta(travado.pk) or _motivo_do_veiculo(travado)
            if erro is not None:
                raise erro
            movimentacao = Movimentacao.objects.create(
                veiculo=travado,
                filial_saida_id=travado.filial_id,
                criada_por=usuario,
                agendada_para=agendada_para,
                status=S.AGENDADA,
                **campos,
            )
            _gravar_paradas(movimentacao, paradas)
            registrar_evento(
                "movimentacao.criar",
                CategoriaAuditoria.OPERACAO,
                objeto=movimentacao,
                depois=retrato(movimentacao),
                regra="MOV-01",
                filial_id=movimentacao.filial_saida_id,
            )
            if sair_agora:
                _iniciar(movimentacao, travado)
    except IntegrityError as erro_banco:
        # A restrição do banco: outra movimentação aberta do veículo, criada ao mesmo tempo.
        conflito = _ja_aberta(veiculo.pk)
        if conflito is None:
            raise
        raise conflito from erro_banco
    return movimentacao


def editar(movimentacao: Movimentacao, dados: dict[str, Any], usuario: Any) -> Movimentacao:
    """Só a `agendada` (CA-246-05): o mesmo corpo, menos o veículo e o "Sair agora"."""
    exigir_gestao(usuario, movimentacao.filial_saida_id)
    if movimentacao.status != S.AGENDADA:
        raise _transicao(movimentacao.status, S.AGENDADA)
    veiculo = Veiculo.objects.select_related("categoria").get(pk=movimentacao.veiculo_id)
    campos = _destino_e_mais(veiculo, dados)
    agendada_para = _agendada_para(dados)
    paradas = campos.pop("paradas")
    with transaction.atomic():
        travada: Movimentacao = Movimentacao.objects.select_for_update().get(pk=movimentacao.pk)
        if travada.status != S.AGENDADA:
            raise _transicao(travada.status, S.AGENDADA)
        with auditar(travada, "movimentacao.editar", CategoriaAuditoria.OPERACAO, regra="MOV-01"):
            for campo, valor in campos.items():
                setattr(travada, campo, valor)
            travada.agendada_para = agendada_para
            travada.save()
            # As paradas da agendada ainda não andaram: trocam todas.
            ParadaMovimentacao.objects.filter(movimentacao=travada).delete()
            _gravar_paradas(travada, paradas)
    return travada


def _iniciar(movimentacao: Movimentacao, veiculo: Veiculo) -> None:
    """Dentro da transação, com a linha do veículo travada (ADR 0028, item 3)."""
    movimentacao.iniciada_em = relogio.agora()
    movimentacao.km_saida = veiculo.km_atual
    estados.transicionar(
        movimentacao,
        S.EM_TRANSITO,
        acao="movimentacao.iniciar",
        regra="MOV-03",
        mais_campos=("iniciada_em", "km_saida"),
    )
    # Só o disponível muda de status; os outros mantêm o dele (MOV-03, CA-246-07).
    if veiculo.status == V.DISPONIVEL:
        veiculos.transicionar(
            veiculo, V.EM_MOVIMENTACAO, origem=_origem(movimentacao), acao="movimentar"
        )


def iniciar(movimentacao: Movimentacao, usuario: Any) -> Movimentacao:
    exigir_gestao(usuario, movimentacao.filial_saida_id)
    with transaction.atomic():
        travada: Movimentacao = Movimentacao.objects.select_for_update().get(pk=movimentacao.pk)
        if travada.status != S.AGENDADA:
            raise _transicao(travada.status, S.EM_TRANSITO)
        veiculo = veiculos.travar(travada.veiculo)
        # Reservado ou alugado depois do agendamento: 409, e ela continua agendada (CA-246-05).
        erro = _motivo_do_veiculo(veiculo)
        if erro is not None:
            raise erro
        _iniciar(travada, veiculo)
    return travada


def cancelar(movimentacao: Movimentacao, motivo: str, usuario: Any) -> Movimentacao:
    """Só a `agendada`; o veículo não muda (CA-246-05, CA-246-06)."""
    exigir_gestao(usuario, movimentacao.filial_saida_id)
    texto = " ".join((motivo or "").split())
    if not texto:
        raise ErroDeValidacao({"motivo": ["Informe o motivo."]})
    with transaction.atomic():
        travada: Movimentacao = Movimentacao.objects.select_for_update().get(pk=movimentacao.pk)
        if travada.status != S.AGENDADA:
            raise _transicao(travada.status, S.CANCELADA)
        travada.cancelada_em = relogio.agora()
        travada.motivo_cancelamento = texto[:200]
        estados.transicionar(
            travada,
            S.CANCELADA,
            motivo=texto[:200],
            acao="movimentacao.cancelar",
            regra="MOV-03",
            mais_campos=("cancelada_em", "motivo_cancelamento"),
        )
    return travada


def cancelar_pela_baixa(veiculo_id: int, motivo_da_baixa: str) -> Movimentacao | None:
    """A baixa do veículo encerra a movimentação aberta dele (MOV-03, decisão do dono de 16 out
    2026, opção B): a agendada e a iniciada viram `cancelada` (a iniciada é a única exceção ao
    "depois de sair, não cancela"), com o motivo da baixa. As despesas das paradas ficam, e na
    transferência o veículo continua na filial de saída."""
    aberta: Movimentacao | None = (
        Movimentacao.objects.select_for_update()
        .filter(veiculo_id=veiculo_id, status__in=ABERTAS)
        .first()
    )
    if aberta is None:
        return None
    motivo = f"Veículo baixado: {motivo_da_baixa}"[:200]
    aberta.cancelada_em = relogio.agora()
    aberta.motivo_cancelamento = motivo
    estados.transicionar(
        aberta,
        S.CANCELADA,
        motivo=motivo,
        acao="movimentacao.cancelar",
        regra="MOV-03",
        mais_campos=("cancelada_em", "motivo_cancelamento"),
    )
    return aberta


# --- Paradas (MOV-04) ---


def proxima_parada(movimentacao: Movimentacao) -> ParadaMovimentacao | None:
    """A parada atual (`no_local`) ou a próxima sem chegada; `None` quando falta só o destino."""
    for parada in movimentacao.paradas.order_by("ordem"):
        if parada.saiu_em is None:
            return parada
    return None


def _parada_fora_de_ordem() -> Conflito:
    return Conflito("parada_fora_de_ordem", "Registre as paradas na ordem da rota.")


def _travada_para_chegada(movimentacao: Movimentacao, usuario: Any) -> Movimentacao:
    exigir_chegada(movimentacao, usuario)
    travada: Movimentacao = Movimentacao.objects.select_for_update().get(pk=movimentacao.pk)
    return travada


def chegar_parada(movimentacao: Movimentacao, parada_id: int, usuario: Any) -> Movimentacao:
    with transaction.atomic():
        travada = _travada_para_chegada(movimentacao, usuario)
        if travada.status != S.EM_TRANSITO:
            raise _transicao(travada.status, S.NO_LOCAL)
        parada = proxima_parada(travada)
        if parada is None or parada.pk != parada_id or parada.chegou_em is not None:
            raise _parada_fora_de_ordem()
        parada.chegou_em = relogio.agora()
        parada.save(update_fields=["chegou_em", "atualizado_em"])
        estados.transicionar(travada, S.NO_LOCAL, acao="movimentacao.chegar_parada", regra="MOV-04")
    return travada


def _dia_local(filial: Filial, momento: datetime) -> date:
    return momento.astimezone(ZoneInfo(filial.fuso)).date()


def sair_parada(
    movimentacao: Movimentacao,
    parada_id: int,
    valor_pago_centavos: int,
    nota: Any,
    usuario: Any,
) -> Movimentacao:
    """Valor acima de zero gera a despesa da parada, pela FIN-05 (MOV-04, CA-246-02, 08, 14)."""
    if valor_pago_centavos < 0:
        raise ErroDeValidacao({"valor_pago_centavos": ["O valor não pode ser negativo."]})
    # Quem não registra a chegada recebe o 403 antes de o servidor ler o arquivo (B-02, T-315).
    exigir_chegada(movimentacao, usuario)
    if nota is not None:
        arquivos.validar(nota, "nota")
    with transaction.atomic():
        travada = _travada_para_chegada(movimentacao, usuario)
        if travada.status != S.NO_LOCAL:
            raise _transicao(travada.status, S.EM_TRANSITO)
        parada = proxima_parada(travada)
        if parada is None or parada.pk != parada_id:
            raise _parada_fora_de_ordem()
        agora = relogio.agora()
        parada.saiu_em = agora
        parada.valor_pago_centavos = valor_pago_centavos
        if valor_pago_centavos > 0:
            filial = Filial.objects.get(pk=travada.filial_saida_id)
            dia = _dia_local(filial, agora)
            parada.despesa = financeiro.lancar_despesa(
                filial=filial,
                usuario=usuario,
                descricao=f"{travada.codigo} · {parada.servico} · {parada.local.nome}",
                valor_centavos=valor_pago_centavos,
                data=dia,
                vencimento=dia,
                categoria=parada.categoria,
                veiculo_id=travada.veiculo_id,
                nota=nota,
                origem=financeiro.Origem(Origem.MOVIMENTACAO, travada.pk, travada.codigo),
            )
        parada.save(update_fields=["saiu_em", "valor_pago_centavos", "despesa", "atualizado_em"])
        estados.transicionar(
            travada, S.EM_TRANSITO, acao="movimentacao.sair_parada", regra="MOV-04"
        )
    return travada


# --- Chegada no destino (MOV-05, MOV-06) ---


def _pronta_para_o_destino(movimentacao: Movimentacao) -> None:
    if movimentacao.status != S.EM_TRANSITO:
        raise _transicao(movimentacao.status, S.CONCLUIDA)
    if proxima_parada(movimentacao) is not None:
        raise _parada_fora_de_ordem()


def enviar_foto(
    movimentacao: Movimentacao, posicao: str, arquivo: Any, usuario: Any
) -> FotoChegadaMovimentacao:
    """Uma por vez; a foto nova da mesma posição substitui a anterior (AUD-05), e cada envio fica
    na auditoria, com a posição, a foto e se substituiu outra (MOV-05, B-01 da T-315)."""
    if posicao not in POSICOES:
        raise ErroDeValidacao({"posicao": ["Escolha frente, traseira, lado esquerdo ou direito."]})
    # O 403 vem antes de decodificar a imagem (B-02, T-315).
    exigir_chegada(movimentacao, usuario)
    formato = arquivos.validar(arquivo)
    if formato.extensao == "pdf":
        raise ErroDeValidacao({"arquivo": ["Envie uma foto JPG ou PNG."]})
    limpa = arquivos.sem_metadados(arquivo, formato)
    with transaction.atomic():
        travada = _travada_para_chegada(movimentacao, usuario)
        if not travada.vistoria_rapida:
            raise Conflito("MOV-05", "Esta movimentação não tem vistoria rápida.")
        _pronta_para_o_destino(travada)
        foto = FotoChegadaMovimentacao.objects.filter(movimentacao=travada, posicao=posicao).first()
        substituiu = foto is not None and bool(foto.arquivo)
        if foto is None:
            # O caminho do arquivo leva o id: a linha nasce antes (ADR 0009).
            foto = FotoChegadaMovimentacao.objects.create(movimentacao=travada, posicao=posicao)
        foto.por = usuario
        foto.arquivo.save(limpa.name, limpa, save=False)
        foto.save(update_fields=["por", "arquivo", "atualizado_em"])
        registrar_evento(
            "movimentacao.foto_chegada",
            CategoriaAuditoria.OPERACAO,
            objeto=travada,
            depois={"posicao": posicao, "foto_id": foto.pk, "substituiu": substituiu},
            regra="MOV-05",
        )
    return foto


def concluir(movimentacao: Movimentacao, dados: dict[str, Any], usuario: Any) -> Movimentacao:
    """`em_transito` → `concluida`, com o km, a vistoria rápida e, na transferência, quem
    recebe. O veículo volta a `disponivel`, ou `indisponivel` com documento vencido (VEI-03);
    na transferência passa a ser da filial de destino (MOV-06)."""
    km = dados.get("km")
    if not isinstance(km, int) or km < 0:
        raise ErroDeValidacao({"km": ["Informe o km."]})
    with transaction.atomic():
        travada = _travada_para_chegada(movimentacao, usuario)
        _pronta_para_o_destino(travada)
        erros: dict[str, list[str]] = {}
        combustivel = dados.get("combustivel") or ""
        if travada.vistoria_rapida:
            if not combustivel:
                erros["combustivel"] = ["Informe o combustível."]
            faltam = len(POSICOES) - travada.fotos_chegada.count()
            if faltam > 0:
                erros["fotos"] = [f"Faltam {faltam} fotos." if faltam > 1 else "Falta 1 foto."]
        recebido_por = None
        if travada.transferencia:
            try:
                recebido_por = _pessoa_da_filial(
                    dados.get("recebido_por_id"),
                    travada.destino_id,
                    "recebido_por_id",
                    NAO_RECEBEM,
                    "Escolha quem recebe entre as pessoas da filial de destino.",
                )
            except ErroDeValidacao as erro:
                erros.update(erro.campos)
        if erros:
            raise ErroDeValidacao(erros)

        veiculo = veiculos.travar(travada.veiculo)
        origem = _origem(travada)
        veiculos.atualizar_km(veiculo, km, origem=origem)
        agora = relogio.agora()
        travada.km_chegada = km
        travada.combustivel_chegada = combustivel if travada.vistoria_rapida else ""
        travada.recebido_por = recebido_por
        travada.concluida_em = agora
        estados.transicionar(
            travada,
            S.CONCLUIDA,
            acao="movimentacao.concluir",
            regra="MOV-05",
            mais_campos=("km_chegada", "combustivel_chegada", "recebido_por", "concluida_em"),
        )
        veiculo.refresh_from_db()
        if veiculo.status == V.EM_MOVIMENTACAO:
            vencidos = veiculos.documentos_vencidos_que_bloqueiam(veiculo, relogio.hoje())
            if vencidos:
                motivo = " e ".join(f"{TipoDocumento(t).label} vencido" for t in vencidos)
                veiculos.transicionar(
                    veiculo, V.INDISPONIVEL, origem=origem, motivo=motivo, acao="chegada"
                )
            else:
                veiculos.transicionar(veiculo, V.DISPONIVEL, origem=origem, acao="chegada")
        if travada.transferencia:
            veiculos.transferir(
                veiculo,
                travada.destino_id,
                travada.codigo,
                categoria_id=travada.categoria_destino_id,
                origem=origem,
            )
    return travada
