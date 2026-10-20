"""Regras de clientes: cadastro, documentos, bloqueio e inativação (CLI-01 a CLI-09, APR-05).

Único lugar que muda um cliente. O status muda só por `comum.estados.transicionar`, com
auditoria. O claro de CPF, CNPJ e CNH entra só por `definir_<campo>` (ADR 0014).
"""

import re
from datetime import date
from typing import Any

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction

from comum import aprovacoes, arquivos, estados, leituras, relogio
from comum.auditoria import Categoria as CategoriaAuditoria
from comum.auditoria import TipoAtor, ator_atual, auditar, registrar_evento, retrato
from comum.campos import buscar_por_hash
from comum.dinheiro import formatar_reais
from comum.documentos import cnpj_valido, cpf_valido, so_digitos
from comum.erros import Conflito, ErroDeRegra, ErroDeValidacao

from . import selectors
from .models import (
    CategoriaCnh,
    Cliente,
    DocumentoCliente,
    MotivoBloqueio,
    StatusCliente,
    TipoCliente,
)

S = StatusCliente
DIAS_PARA_BLOQUEIO = 15  # CLI-05, LOC-07

CAMPOS_SIMPLES = ("nome", "celular", "email", "profissao", "nascimento")
CAMPOS_ENDERECO = ("cep", "logradouro", "numero", "complemento", "bairro", "cidade", "uf")
CAMPOS_REFERENCIA = {"nome": "referencia_nome", "parentesco": "referencia_parentesco"}
CAMPOS_REFERENCIA_TELEFONE = ("telefone", "referencia_telefone")
CAMPOS_CNH = {
    "categoria": "cnh_categoria",
    "validade": "cnh_validade",
    "primeira_habilitacao": "cnh_primeira_habilitacao",
}


def _quem() -> int | None:
    ator = ator_atual()
    return ator.id if ator.tipo == TipoAtor.USUARIO else None


def _exigir_motivo(motivo: str | None) -> str:
    texto = (motivo or "").strip()
    if not texto:
        raise ErroDeValidacao({"motivo": ["Informe o motivo."]})
    return texto


def _travar_id(cliente_id: int) -> Cliente:
    travado: Cliente = Cliente.objects.select_for_update().get(pk=cliente_id)
    return travado


def _travar(cliente: Cliente) -> Cliente:
    return _travar_id(cliente.pk)


def _recarregar(cliente: Cliente) -> None:
    cliente.refresh_from_db()
    cliente._status_salvo = cliente.status


# --- Validação da entrada (CLI-01) ---


def _telefone(valor: str | None, campo: str, erros: dict[str, list[str]]) -> str:
    digitos = so_digitos(valor or "")
    if digitos and not 10 <= len(digitos) <= 13:
        erros.setdefault(campo, []).append("Telefone inválido.")
    return digitos


def _documento(tipo: str, valor: str, erros: dict[str, list[str]]) -> str:
    digitos = so_digitos(valor)
    if tipo == TipoCliente.PF and not cpf_valido(digitos):
        erros["documento"] = ["CPF inválido."]
    if tipo == TipoCliente.PJ and not cnpj_valido(digitos):
        erros["documento"] = ["CNPJ inválido."]
    return digitos


def _limpar(tipo: str, dados: dict[str, Any]) -> dict[str, Any]:
    """Campos do model a gravar, a partir do corpo de POST ou PATCH. Objeto aninhado nulo
    apaga o grupo inteiro; chave vazia ou nula apaga só o campo."""
    erros: dict[str, list[str]] = {}
    limpos: dict[str, Any] = {}
    for campo in CAMPOS_SIMPLES:
        if campo in dados:
            valor = dados[campo]
            limpos[campo] = valor.strip() if isinstance(valor, str) else valor
    if "celular" in limpos:
        limpos["celular"] = _telefone(limpos["celular"], "celular", erros)
        if not limpos["celular"]:
            erros["celular"] = ["Informe o celular."]
    if "nome" in limpos and not limpos["nome"]:
        erros["nome"] = ["Informe o nome."]
    if tipo == TipoCliente.PJ:
        limpos.pop("nascimento", None)  # não se aplica à PJ
    for campo in ("email", "profissao"):
        if campo in limpos and limpos[campo] is None:
            limpos[campo] = ""
    if "documento" in dados:
        limpos["documento"] = _documento(tipo, dados["documento"] or "", erros)

    if "endereco" in dados:
        endereco = dados["endereco"] or {}
        for campo in CAMPOS_ENDERECO:
            if dados["endereco"] is None or campo in endereco:
                limpos[campo] = (endereco.get(campo) or "").strip()
        if limpos.get("cep"):
            limpos["cep"] = so_digitos(limpos["cep"])
            if len(limpos["cep"]) != 8:
                erros["endereco.cep"] = ["CEP inválido."]
        if limpos.get("uf"):
            limpos["uf"] = limpos["uf"].upper()
            if not re.fullmatch(r"[A-Z]{2}", limpos["uf"]):
                erros["endereco.uf"] = ["UF inválida."]

    if "referencia" in dados:
        referencia = dados["referencia"] or {}
        for chave, campo in CAMPOS_REFERENCIA.items():
            if dados["referencia"] is None or chave in referencia:
                limpos[campo] = (referencia.get(chave) or "").strip()
        chave, campo = CAMPOS_REFERENCIA_TELEFONE
        if dados["referencia"] is None or chave in referencia:
            limpos[campo] = _telefone(referencia.get(chave), "referencia.telefone", erros)

    if "cnh" in dados:
        cnh = dados["cnh"] or {}
        for chave, campo in CAMPOS_CNH.items():
            if dados["cnh"] is None or chave in cnh:
                limpos[campo] = cnh.get(chave) or ("" if chave == "categoria" else None)
        if dados["cnh"] is None or "numero" in cnh:
            limpos["cnh_numero"] = so_digitos(cnh.get("numero") or "")

    if "responsavel" in dados and tipo == TipoCliente.PJ:
        responsavel = dados["responsavel"] or {}
        if dados["responsavel"] is None or "nome" in responsavel:
            limpos["responsavel_nome"] = (responsavel.get("nome") or "").strip()
        if dados["responsavel"] is None or "cpf" in responsavel:
            cpf = so_digitos(responsavel.get("cpf") or "")
            if cpf and not cpf_valido(cpf):
                erros["responsavel.cpf"] = ["CPF inválido."]
            limpos["responsavel_cpf"] = cpf
        if dados["responsavel"] is None or "celular" in responsavel:
            limpos["responsavel_celular"] = _telefone(
                responsavel.get("celular"), "responsavel.celular", erros
            )
    if erros:
        raise ErroDeValidacao(erros)
    return limpos


def documento_repetido(cliente: Cliente) -> Conflito:
    nome_doc = "CPF" if cliente.tipo == TipoCliente.PF else "CNPJ"
    return Conflito(
        "CLI-01",
        f"Já existe um cliente com este {nome_doc}",
        {"cliente_id": cliente.pk, "nome": cliente.nome},
    )


def _conferir_unico(documento: str, exceto: int | None = None) -> None:
    """CLI-01: único por empresa, conferido pelo hash (ADR 0014)."""
    existente = (
        Cliente.objects.filter(documento_hash=buscar_por_hash(documento)).exclude(pk=exceto).first()
    )
    if existente is not None:
        raise documento_repetido(existente)


def _aplicar(cliente: Cliente, limpos: dict[str, Any]) -> None:
    cifrados = {"documento", "cnh_numero", "responsavel_cpf"}
    for campo, valor in limpos.items():
        if campo in cifrados:
            getattr(cliente, f"definir_{campo}")(valor)
        else:
            setattr(cliente, campo, valor)


def _consentir(cliente: Cliente, consentimento: bool | None) -> None:
    """`true` grava o momento do servidor uma vez; `false` não apaga (revogar é AUD-06)."""
    if consentimento and cliente.consentimento_em is None:
        cliente.consentimento_em = relogio.agora()


def _gravar_unico(cliente: Cliente, **kwargs: Any) -> None:
    """A unicidade do hash também vale na corrida entre dois cadastros iguais."""
    try:
        with transaction.atomic():
            cliente.save(**kwargs)
    except IntegrityError as erro:
        if "documento_hash" not in str(erro):
            raise
        existente = Cliente.objects.get(documento_hash=cliente.documento_hash)
        raise documento_repetido(existente) from erro


def acertar_cadastro(cliente: Cliente) -> None:
    """CLI-03: entre `incompleto` e `ativo`, conforme as pendências. Bloqueado e inativo não
    mudam por aqui."""
    if cliente.status not in (S.INCOMPLETO, S.ATIVO):
        return
    alvo = S.INCOMPLETO if selectors.pendencias(cliente) else S.ATIVO
    if alvo != cliente.status:
        acao = "cliente.completar_cadastro" if alvo == S.ATIVO else "cliente.ficou_incompleto"
        estados.transicionar(cliente, alvo, acao=acao, regra="CLI-03")


def cadastrar(dados: dict[str, Any]) -> Cliente:
    """CLI-01, CLI-03. Obrigatórios: tipo, nome, documento e celular; o resto pode faltar e o
    cliente nasce `incompleto`."""
    tipo = dados["tipo"]
    limpos = _limpar(tipo, dados)
    with transaction.atomic():
        _conferir_unico(limpos["documento"])
        cliente = Cliente(tipo=tipo, cliente_desde=relogio.hoje(), status=S.INCOMPLETO)
        _aplicar(cliente, limpos)
        _consentir(cliente, dados.get("consentimento"))
        _gravar_unico(cliente)
        registrar_evento(
            "cliente.cadastrar",
            CategoriaAuditoria.OPERACAO,
            objeto=cliente,
            depois=retrato(cliente),
            regra="CLI-01",
        )
        acertar_cadastro(cliente)
    return cliente


def validar_novo(dados: dict[str, Any]) -> list[dict[str, str]]:
    """IMP-02: as validações de `cadastrar` (e do formato que o serializer confere: e-mail e
    categoria da CNH), sem gravar. Recebe o corpo do POST e devolve `[{campo, codigo,
    mensagem}]`, vazia quando cabe cadastrar. O documento sai com `CLI-01`.

    As mensagens nunca repetem o valor: a importação guarda os erros sem cifra."""
    erros: list[dict[str, str]] = []

    def erro(campo: str, mensagem: str) -> None:
        codigo = "CLI-01" if campo == "documento" else "validacao"
        erros.append({"campo": campo, "codigo": codigo, "mensagem": mensagem})

    tipo = dados.get("tipo")
    if tipo not in TipoCliente.values:
        erro("tipo", "Use pf ou pj.")
        return erros
    for campo, mensagem in (("documento", "Informe o documento."), ("nome", "Informe o nome.")):
        if not str(dados.get(campo) or "").strip():
            erro(campo, mensagem)
    if not str(dados.get("celular") or "").strip():
        erro("celular", "Informe o celular.")
    try:
        _limpar(tipo, dados)
    except ErroDeValidacao as invalido:
        ja_tem = {e["campo"] for e in erros}
        for campo, mensagens in invalido.campos.items():
            for mensagem in mensagens if campo not in ja_tem else []:
                erro(campo, mensagem)
    email = str(dados.get("email") or "").strip()
    if email:
        try:
            validate_email(email)
        except ValidationError:
            erro("email", "E-mail inválido.")
    categoria = ((dados.get("cnh") or {}).get("categoria") or "").strip().upper()
    if categoria and categoria not in CategoriaCnh.values:
        erro("cnh.categoria", "Categoria da CNH inválida.")
    documento = so_digitos(str(dados.get("documento") or ""))
    if documento and not any(e["campo"] == "documento" for e in erros):
        try:
            _conferir_unico(documento)
        except Conflito as conflito:
            erro("documento", conflito.mensagem)
    return erros


def editar(cliente: Cliente, dados: dict[str, Any]) -> Cliente:
    """PATCH: qualquer campo menos `tipo`. Trocar o documento passa pelo CLI-01 de novo."""
    with transaction.atomic():
        travado = _travar(cliente)
        limpos = _limpar(travado.tipo, dados)
        if "documento" in limpos:
            _conferir_unico(limpos["documento"], exceto=travado.pk)
        with auditar(travado, "cliente.editar", CategoriaAuditoria.OPERACAO):
            _aplicar(travado, limpos)
            _consentir(travado, dados.get("consentimento"))
            _gravar_unico(travado)
        acertar_cadastro(travado)
    _recarregar(cliente)
    return cliente


# --- Documentos (CLI-03, AUD-05) ---


def enviar_documento(cliente: Cliente, tipo: str, arquivo: Any) -> DocumentoCliente:
    """O ativo do mesmo tipo fica inativo e guardado. A foto é reprocessada sem metadados."""
    formato = arquivos.validar(arquivo)
    limpo = arquivos.sem_metadados(arquivo, formato)
    with transaction.atomic():
        travado = _travar(cliente)
        for anterior in DocumentoCliente.ativos.select_for_update().filter(
            cliente=travado, tipo=tipo
        ):
            with auditar(anterior, "documento_cliente.substituir", CategoriaAuditoria.OPERACAO):
                anterior.ativo = False
                anterior.save(update_fields=["ativo", "atualizado_em"])
        documento = DocumentoCliente.objects.create(cliente=travado, tipo=tipo, por_id=_quem())
        documento.arquivo.save(limpo.name, limpo, save=True)
        registrar_evento(
            "documento_cliente.enviar",
            CategoriaAuditoria.OPERACAO,
            objeto=documento,
            depois=retrato(documento),
            regra="CLI-03",
        )
        acertar_cadastro(travado)
    _recarregar(cliente)
    return documento


# --- Bloqueio (CLI-05, APR-05) ---


def _status_ao_desbloquear(cliente: Cliente) -> str:
    return S.INCOMPLETO if selectors.pendencias(cliente) else S.ATIVO


def _bloquear(cliente: Cliente, motivo: str, descricao: str, *, regra: str) -> None:
    cliente.bloqueio_motivo = motivo
    cliente.bloqueio_desde = relogio.agora()
    cliente.bloqueio_descricao = descricao[:200]
    estados.transicionar(
        cliente,
        S.BLOQUEADO,
        motivo=descricao,
        acao="cliente.bloquear",
        regra=regra,
        mais_campos=("bloqueio_motivo", "bloqueio_desde", "bloqueio_descricao"),
    )


def _desbloquear(cliente: Cliente, motivo: str, *, acao: str, regra: str = "CLI-05") -> None:
    cliente.bloqueio_motivo = ""
    cliente.bloqueio_desde = None
    cliente.bloqueio_descricao = ""
    estados.transicionar(
        cliente,
        _status_ao_desbloquear(cliente),
        motivo=motivo,
        acao=acao,
        regra=regra,
        mais_campos=("bloqueio_motivo", "bloqueio_desde", "bloqueio_descricao"),
    )


def ja_bloqueado(cliente: Cliente) -> Conflito:
    return Conflito(
        "transicao_cliente",
        "O cliente já está bloqueado.",
        {"de": cliente.status, "para": S.BLOQUEADO},
    )


def bloquear(cliente: Cliente, motivo: str) -> Cliente:
    """Gerente e administrador, na hora, com motivo (CLI-05). Só sai pela mão de alguém."""
    texto = _exigir_motivo(motivo)
    with transaction.atomic():
        travado = _travar(cliente)
        if travado.status == S.BLOQUEADO:
            raise ja_bloqueado(travado)
        _bloquear(travado, MotivoBloqueio.MANUAL, texto, regra="CLI-05")
    _recarregar(cliente)
    return cliente


def nao_bloqueado(cliente: Cliente) -> Conflito:
    return Conflito(
        "transicao_cliente",
        "O cliente não está bloqueado.",
        {"de": cliente.status, "para": S.ATIVO},
    )


def desbloquear(cliente: Cliente, motivo: str) -> Cliente:
    """Gerente e administrador desbloqueiam direto, com motivo e auditoria (CLI-05). Um pedido
    APR-05 que estava pendente perde o sentido e é cancelado."""
    texto = _exigir_motivo(motivo)
    with transaction.atomic():
        travado = _travar(cliente)
        if travado.status != S.BLOQUEADO:
            raise nao_bloqueado(travado)
        _desbloquear(travado, texto, acao="cliente.desbloquear")
        aprovacoes.cancelar_pendentes(
            origem_tipo="cliente", origem_id=travado.pk, motivo="Cliente desbloqueado"
        )
    _recarregar(cliente)
    return cliente


def pedir_desbloqueio(
    cliente: Cliente, motivo: str, solicitante: Any, filial_id: int
) -> aprovacoes.PedidoRef:
    """Vendedor: abre o APR-05 (ADR 0019) e o cliente continua bloqueado até o gerente
    aprovar. Pedido igual pendente: 409 `pedido_pendente`."""
    texto = _exigir_motivo(motivo)
    with transaction.atomic():
        travado = _travar(cliente)
        if travado.status != S.BLOQUEADO:
            raise nao_bloqueado(travado)
        return aprovacoes.pedir(
            tipo="APR-05",
            origem_tipo="cliente",
            origem_id=travado.pk,
            origem_codigo=None,
            filial_id=filial_id,
            solicitante=solicitante,
            titulo="Desbloqueio de cliente",
            detalhe=f"{travado.nome} · {texto}",
            motivo=texto,
            resumo=_resumo_do_desbloqueio(travado),
        )


def _resumo_do_desbloqueio(cliente: Cliente) -> aprovacoes.Resumo:
    """O cartão do APR-05 (T-201): o bloqueio (automático, com os dias de atraso do pedido; ou
    manual, com o motivo) e a situação das contas. Sem CPF nem contato."""
    contagem = leituras.contar(
        selectors.ALVO,
        cliente.pk,
        [selectors.CONTADOR_DIAS_DE_ATRASO, "contas_vencidas", "em_aberto_centavos"],
    )
    if cliente.bloqueio_motivo == MotivoBloqueio.ATRASO:
        bloqueio = f"Automático · {contagem[selectors.CONTADOR_DIAS_DE_ATRASO]} dias de atraso"
    else:
        bloqueio = f"Manual · {cliente.bloqueio_descricao or cliente.get_bloqueio_motivo_display()}"
    vencidas = contagem["contas_vencidas"]
    contas = (
        f"{vencidas} em atraso · {formatar_reais(contagem['em_aberto_centavos'])}"
        if vencidas
        else "Em dia"
    )
    return aprovacoes.Resumo(
        [("Bloqueio", bloqueio), ("Contas", contas)], "Aprovado, o cadastro volta a ativo."
    )


def aplicar_desbloqueio_aprovado(cliente_id: int, motivo: str) -> Cliente | None:
    """APR-05 aprovado (assinante de `aprovacoes.pedido_decidido`). Se o cliente já saiu do
    bloqueio por outro caminho, não há o que fazer."""
    with transaction.atomic():
        travado = _travar_id(cliente_id)
        if travado.status != S.BLOQUEADO:
            return travado
        _desbloquear(
            travado, motivo or "Desbloqueio aprovado", acao="cliente.desbloquear", regra="APR-05"
        )
    return travado


def bloquear_por_atraso(cliente_id: int, dias_atraso: int, vencimento: date | None) -> bool:
    """Assinante de `financeiro.parcela_atrasou` (CLI-05, LOC-07): com 15 dias de atraso o
    cliente é bloqueado e desbloqueia sozinho ao quitar. Já bloqueado ou inativo: nada muda."""
    if dias_atraso < DIAS_PARA_BLOQUEIO:
        return False
    with transaction.atomic():
        travado = _travar_id(cliente_id)
        if travado.status not in (S.ATIVO, S.INCOMPLETO):
            return False
        quando = f" desde {vencimento:%d/%m/%Y}" if vencimento else ""
        _bloquear(
            travado,
            MotivoBloqueio.ATRASO,
            f"Conta com {dias_atraso} dias de atraso{quando}",
            regra="CLI-05",
        )
    return True


def desbloquear_por_quitacao(cliente_id: int) -> bool:
    """Assinante de `financeiro.parcela_paga`: só o bloqueio por atraso sai sozinho, e só
    quando não resta conta com 15 dias ou mais de atraso (CLI-05)."""
    with transaction.atomic():
        travado = _travar_id(cliente_id)
        if travado.status != S.BLOQUEADO or travado.bloqueio_motivo != MotivoBloqueio.ATRASO:
            return False
        if selectors.contas_com_atraso_para_bloqueio(travado.pk) > 0:
            return False
        _desbloquear(travado, "Contas em atraso quitadas", acao="cliente.desbloquear_quitado")
    return True


# --- Inativar (CLI-09) ---


def inativar(cliente: Cliente, motivo: str) -> Cliente:
    """Recusado com locação aberta, valor em aberto ou venda aberta (422)."""
    texto = _exigir_motivo(motivo)
    with transaction.atomic():
        travado = _travar(cliente)
        pendencia = selectors.pendencias_para_inativar(travado)
        if any(pendencia.values()):
            raise ErroDeRegra(
                "cliente_com_pendencia",
                "O cliente tem locação, venda ou valor em aberto.",
                pendencia,
            )
        estados.transicionar(
            travado, S.INATIVO, motivo=texto, acao="cliente.inativar", regra="CLI-09"
        )
    _recarregar(cliente)
    return cliente


def reativar(cliente: Cliente, motivo: str) -> Cliente:
    """Volta a `ativo` ou `incompleto`, conforme o cadastro (CLI-03, CLI-09)."""
    texto = _exigir_motivo(motivo)
    with transaction.atomic():
        travado = _travar(cliente)
        if travado.status != S.INATIVO:
            raise Conflito(
                "transicao_cliente",
                "O cliente não está inativo.",
                {"de": travado.status, "para": S.ATIVO},
            )
        estados.transicionar(
            travado,
            _status_ao_desbloquear(travado),
            motivo=texto,
            acao="cliente.reativar",
            regra="CLI-09",
        )
    _recarregar(cliente)
    return cliente
