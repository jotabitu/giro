"""Regras da vistoria (VIS-01 a VIS-04, VEI-01, VEI-02, VEI-03, CLI-02, CLI-03, CLI-05) e da
devolução com acerto (DEV-01 a DEV-06, LOC-10 a LOC-13).

O único lugar que muda uma vistoria ou uma devolução. A saída concluída chama
`locacoes.services.registrar_vistoria_saida`, que pode ativar a locação, e o encerramento da
devolução chama `locacoes.services.encerrar` (ADR 0011: `vistorias` fica acima de `locacoes` e
de `financeiro`).
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction

from apps.clientes import selectors as clientes_selectors
from apps.financeiro import selectors as financeiro_selectors
from apps.financeiro import services as financeiro
from apps.financeiro.models import ContaReceber, StatusConta, TipoConta
from apps.locacoes import services as locacoes
from apps.locacoes.models import Locacao, Periodicidade, StatusLocacao
from apps.veiculos import services as veiculos
from apps.veiculos.models import Origem, StatusVeiculo, Veiculo
from comum import arquivos, estados, relogio
from comum.auditoria import Categoria, auditar, registrar_evento, retrato
from comum.dinheiro import formatar_reais
from comum.erros import (
    Conflito,
    ErroDeRegra,
    ErroDeValidacao,
    NaoEncontrado,
    TransicaoInvalida,
)
from comum.eventos import publicar
from comum.tarefas import schema_atual

from . import acerto as conta
from .models import (
    POSICOES_OBRIGATORIAS,
    Avaria,
    Devolucao,
    FotoVistoria,
    ItemAcerto,
    ModoItem,
    NaturezaItem,
    PosicaoFoto,
    StatusDevolucao,
    StatusVistoria,
    TipoItemAcerto,
    TipoVistoria,
    Vistoria,
)

S = StatusVistoria

# VIS-02: a lista padrão do ramo, na ordem da tela. Motos e carros usam a mesma por enquanto.
ITENS_PADRAO: dict[str, list[tuple[str, str]]] = {
    tipo: [
        ("pneus_freios", "Pneus e freios"),
        ("luzes_buzina", "Luzes e buzina"),
        ("retrovisores", "Retrovisores"),
        ("documento_chave", "Documento e chave"),
        ("acessorios", "Acessórios entregues"),
    ]
    for tipo in ("moto", "carro")
}
ROTULO_POSICAO = dict(PosicaoFoto.choices)


@dataclass
class Pendencia:
    """Um motivo para não concluir; `detalhes` sobem para os detalhes do 422."""

    codigo: str
    mensagem: str
    curta: str  # o nome em `pendencias` da representação
    detalhes: dict[str, Any] = field(default_factory=dict)

    def como_dict(self) -> dict[str, Any]:
        return {"codigo": self.codigo, "mensagem": self.mensagem, **self.detalhes}


def _quem(usuario: Any) -> int | None:
    return getattr(usuario, "pk", None)


def _travar(vistoria: Vistoria) -> Vistoria:
    travada: Vistoria = Vistoria.objects.select_for_update().get(pk=vistoria.pk)
    return travada


def _recarregar(vistoria: Vistoria) -> None:
    vistoria.refresh_from_db()
    vistoria._status_salvo = vistoria.status


def _origem(vistoria: Vistoria, locacao: Locacao) -> veiculos.OrigemDaMudanca:
    return veiculos.OrigemDaMudanca(Origem.VISTORIA, vistoria.pk, locacao.codigo)


def concluida_nao_se_edita() -> Conflito:
    return Conflito(
        "vistoria_concluida",
        "A vistoria concluída não se edita. Para corrigir, use Corrigir vistoria.",
    )


def _exigir_rascunho(vistoria: Vistoria) -> None:
    if vistoria.status != S.RASCUNHO:
        raise concluida_nao_se_edita()


# --- Criar (VIS-02) ---


def itens_iniciais(locacao: Locacao, veiculo: Veiculo) -> list[dict[str, Any]]:
    """A lista do ramo e os extras da locação como itens ("Capacete extra")."""
    padrao = ITENS_PADRAO[veiculo.categoria.tipo_veiculo]
    extras = [(f"extra_{e.pk}", e.nome) for e in locacao.extras.order_by("id")]
    return [
        {"codigo": codigo, "rotulo": rotulo, "ok": None, "observacao": None}
        for codigo, rotulo in [*padrao, *extras]
    ]


def _rascunho(locacao: Locacao, veiculo: Veiculo, tipo: str) -> Vistoria | None:
    return Vistoria.objects.filter(
        locacao=locacao, veiculo=veiculo, tipo=tipo, status=S.RASCUNHO
    ).first()


def _vigente(locacao: Locacao, veiculo: Veiculo, tipo: str) -> Vistoria | None:
    return Vistoria.objects.filter(
        locacao=locacao, veiculo=veiculo, tipo=tipo, status=S.CONCLUIDA, vigente=True
    ).first()


def criar(locacao: Locacao, tipo: str, usuario: Any) -> tuple[Vistoria, bool]:
    """A vistoria em `rascunho` do veículo atual, com a lista pronta. Se já existe rascunho do
    mesmo tipo, devolve ele (`criada = False`): quem vistoria continua de onde parou."""
    veiculo = Veiculo.objects.select_related("categoria").get(pk=locacao.veiculo_id)
    existente = _rascunho(locacao, veiculo, tipo)
    if existente is not None:
        return existente, False
    if _vigente(locacao, veiculo, tipo) is not None:
        raise Conflito(
            "vistoria_concluida",
            "Esta vistoria já foi concluída. Para corrigir, use Corrigir vistoria.",
        )
    try:
        with transaction.atomic():
            vistoria = Vistoria.objects.create(
                locacao=locacao,
                veiculo=veiculo,
                tipo=tipo,
                itens=itens_iniciais(locacao, veiculo),
                responsavel_id=_quem(usuario),
            )
            registrar_evento(
                f"vistoria.iniciar_{tipo}",
                Categoria.OPERACAO,
                objeto=vistoria,
                depois=retrato(vistoria),
            )
    except IntegrityError:  # outra pessoa abriu o rascunho ao mesmo tempo
        concorrente = _rascunho(locacao, veiculo, tipo)
        if concorrente is None:
            raise
        return concorrente, False
    return vistoria, True


def iniciar_saida(locacao: Locacao, usuario: Any) -> tuple[Vistoria, bool]:
    """Saída só para locação `aguardando_retirada`. A troca de veículo (LOC-09) chega na T-092."""
    if locacao.status != StatusLocacao.AGUARDANDO_RETIRADA:
        raise TransicaoInvalida(
            "transicao_locacao",
            "A vistoria de saída é só para locação aguardando retirada.",
            {"status": locacao.status},
        )
    return criar(locacao, TipoVistoria.SAIDA, usuario)


# --- Preencher ("Salvar e continuar depois" é só este passo, DEV-05) ---


def _itens_respondidos(atuais: list[dict[str, Any]], respostas: list[dict[str, Any]]) -> list[Any]:
    por_codigo = {item["codigo"]: dict(item) for item in atuais}
    desconhecidos = [r["codigo"] for r in respostas if r["codigo"] not in por_codigo]
    if desconhecidos:
        raise ErroDeValidacao({"itens": [f"Item desconhecido: {', '.join(desconhecidos)}."]})
    for resposta in respostas:
        item = por_codigo[resposta["codigo"]]
        item["ok"] = resposta.get("ok")
        if "observacao" in resposta:
            item["observacao"] = (resposta["observacao"] or "").strip() or None
    return [por_codigo[item["codigo"]] for item in atuais]


def editar(vistoria: Vistoria, dados: dict[str, Any], usuario: Any) -> Vistoria:
    """`{km?, combustivel?, itens?, observacoes?}`, só em rascunho (VIS-04)."""
    with transaction.atomic():
        travada = _travar(vistoria)
        _exigir_rascunho(travada)
        if "km" in dados:
            travada.km = dados["km"]
        if "combustivel" in dados:
            travada.combustivel = dados["combustivel"] or ""
        if "itens" in dados:
            travada.itens = _itens_respondidos(travada.itens, dados["itens"])
        if "observacoes" in dados:
            travada.observacoes = (dados["observacoes"] or "").strip()
        travada.responsavel_id = _quem(usuario)
        travada.save()
    _recarregar(vistoria)
    return vistoria


def enviar_foto(vistoria: Vistoria, posicao: str, arquivo: Any, usuario: Any) -> FotoVistoria:
    """JPG ou PNG até 10 MB, reprocessada sem metadados (sem GPS, AUD-05). A nova foto de posição
    fixa deixa a anterior inativa e guardada; as de avaria se somam."""
    formato = arquivos.validar(arquivo)
    if formato.extensao == "pdf":
        raise ErroDeValidacao({"arquivo": ["Envie uma foto JPG ou PNG."]})
    limpo = arquivos.sem_metadados(arquivo, formato)
    with transaction.atomic():
        travada = _travar(vistoria)
        _exigir_rascunho(travada)
        if posicao != PosicaoFoto.AVARIA:
            for anterior in FotoVistoria.ativos.select_for_update().filter(
                vistoria=travada, posicao=posicao
            ):
                anterior.ativo = False
                anterior.save(update_fields=["ativo", "atualizado_em"])
        foto = FotoVistoria.objects.create(
            vistoria=travada, posicao=posicao, tirada_em=relogio.agora(), por_id=_quem(usuario)
        )
        foto.arquivo.save(limpo.name, limpo, save=True)
    return foto


def registrar_avaria(vistoria: Vistoria, dados: dict[str, Any], usuario: Any) -> Avaria:
    """Na saída, a avaria é preexistente: só registro, sem valor nem oficina (VIS-01). Na chegada,
    `valor_centavos` vem só de quem vê o acerto (o vistoriador não informa valores)."""
    with transaction.atomic():
        travada = _travar(vistoria)
        _exigir_rascunho(travada)
        saida = travada.tipo == TipoVistoria.SAIDA
        erros: dict[str, list[str]] = {}
        valor = dados.get("valor_centavos")
        if valor is not None and getattr(usuario, "perfil", "") == "vistoriador":
            erros["valor_centavos"] = ["O vistoriador não informa valores."]
        elif valor is not None and saida:
            erros["valor_centavos"] = ["Na saída, a avaria só é registrada, sem valor."]
        if saida and dados.get("vai_para_oficina"):
            erros["vai_para_oficina"] = ["Na saída, a avaria só é registrada."]
        foto = FotoVistoria.ativos.filter(vistoria=travada, pk=dados.get("foto_id")).first()
        if foto is None:
            erros["foto_id"] = ["Tire a foto da avaria nesta vistoria."]
        if erros:
            raise ErroDeValidacao(erros)
        avaria = Avaria.objects.create(
            vistoria=travada,
            veiculo_id=travada.veiculo_id,
            descricao=dados["descricao"].strip(),
            preexistente=saida,
            valor_centavos=valor,
            vai_para_oficina=bool(dados.get("vai_para_oficina")),
            foto=foto,
        )
    return avaria


def remover_avaria(vistoria: Vistoria, avaria_id: int) -> None:
    """Avaria nova de um rascunho ainda não é registro de negócio: sai de verdade."""
    with transaction.atomic():
        travada = _travar(vistoria)
        _exigir_rascunho(travada)
        apagadas, _ = Avaria.objects.filter(vistoria=travada, pk=avaria_id).delete()
        if not apagadas:
            raise ErroDeValidacao({"avaria_id": ["Esta avaria não é desta vistoria."]})


# --- Concluir (VIS-01 a VIS-04, VEI-01 a VEI-03, CLI-02, CLI-03, CLI-05) ---


def _faltam_fotos(vistoria: Vistoria) -> list[str]:
    feitas = set(FotoVistoria.ativos.filter(vistoria=vistoria).values_list("posicao", flat=True))
    return [p for p in POSICOES_OBRIGATORIAS if p not in feitas]


def _lista(rotulos: list[str]) -> str:
    return rotulos[0] if len(rotulos) == 1 else f"{', '.join(rotulos[:-1])} e {rotulos[-1]}"


def pendencias_da_vistoria(vistoria: Vistoria, veiculo: Veiculo) -> list[Pendencia]:
    """O que falta preencher: fotos, itens, combustível e km."""
    pendencias = []
    faltam = _faltam_fotos(vistoria)
    if faltam:
        nomes = _lista([str(ROTULO_POSICAO[p]).lower() for p in faltam])
        pendencias.append(
            Pendencia("VIS-01", f"Faltam as fotos: {nomes}.", "fotos", {"faltam": faltam})
        )
    sem_resposta = [i["codigo"] for i in vistoria.itens if i.get("ok") is None]
    if sem_resposta:
        pendencias.append(
            Pendencia("VIS-02", "Responda todos os itens.", "itens", {"itens": sem_resposta})
        )
    if not vistoria.combustivel:
        pendencias.append(Pendencia("VIS-03", "Informe o nível do combustível.", "combustivel"))
    if vistoria.km is None:
        pendencias.append(Pendencia("km_nao_informado", "Informe o km do painel.", "km"))
    elif vistoria.km < veiculo.km_atual:
        erro = veiculos.km_menor(veiculo.km_atual)
        pendencias.append(
            Pendencia(
                erro.codigo,
                erro.mensagem,
                "km",
                {
                    "km_atual": veiculo.km_atual,
                    "corrigir_km": f"/api/veiculos/{veiculo.pk}/corrigir-km/",
                },
            )
        )
    return pendencias


def impedimentos_da_retirada(locacao: Locacao, veiculo: Veiculo) -> list[Pendencia]:
    """Só na saída: o cliente liberado (CLI-02, CLI-03, CLI-05) e o CRLV e o seguro em dia
    (VEI-03, decisão de 08 out 2026)."""
    hoje = locacoes.data_local(relogio.agora(), locacao.filial)
    pendencias = [
        Pendencia(i["codigo"], i["mensagem"], "cliente")
        for i in clientes_selectors.impedimentos_para_retirada(
            locacao.cliente, veiculo.categoria.tipo_veiculo, hoje
        )
    ]
    vencidos = veiculos.documentos_vencidos_que_bloqueiam(veiculo, hoje)
    if vencidos:
        erro = veiculos.documento_vencido(vencidos, antes="da retirada")
        pendencias.append(
            Pendencia(erro.codigo, erro.mensagem, "documentos", {"documentos": vencidos})
        )
    return pendencias


def nao_conclui(pendencias: list[Pendencia]) -> ErroDeRegra:
    """422 com todas as pendências; o código e a mensagem são os da primeira, e os detalhes de
    cada uma (ex.: `documentos` da VEI-03) sobem para os detalhes."""
    primeira = pendencias[0]
    mensagem = (
        primeira.mensagem
        if len(pendencias) == 1
        else f"Resolva as {len(pendencias)} pendências antes de concluir."
    )
    detalhes: dict[str, Any] = {}
    for pendencia in pendencias:
        detalhes.update(pendencia.detalhes)
    detalhes["pendencias"] = [p.como_dict() for p in pendencias]
    return ErroDeRegra(primeira.codigo, mensagem, detalhes)


def concluir(vistoria: Vistoria, usuario: Any) -> Vistoria:
    """Numa transação: confere tudo, conclui (não se edita mais, VIS-04), atualiza o km do
    veículo (VEI-02) e, na saída, chama a ativação da locação. A correção concluída passa a ser a
    vigente, e a anterior fica guardada."""
    with transaction.atomic():
        travada = _travar(vistoria)
        _exigir_rascunho(travada)
        locacao = Locacao.objects.select_related("cliente", "filial").get(pk=travada.locacao_id)
        veiculo = Veiculo.objects.select_related("categoria").get(pk=travada.veiculo_id)
        saida = travada.tipo == TipoVistoria.SAIDA
        pendencias = pendencias_da_vistoria(travada, veiculo)
        if saida and travada.substitui_id is None:
            pendencias += impedimentos_da_retirada(locacao, veiculo)
        if pendencias:
            raise nao_conclui(pendencias)

        agora = relogio.agora()
        if travada.substitui_id is not None:
            anterior = Vistoria.objects.select_for_update().get(pk=travada.substitui_id)
            with auditar(
                anterior,
                "vistoria.substituir",
                Categoria.OPERACAO,
                motivo=travada.motivo_correcao,
                regra="VIS-04",
            ):
                anterior.vigente = False
                anterior.save(update_fields=["vigente", "atualizado_em"])
        travada.concluida_em = agora
        travada.responsavel_id = _quem(usuario)
        estados.transicionar(
            travada,
            S.CONCLUIDA,
            acao=f"vistoria.concluir_{travada.tipo}",
            regra="VIS-04",
            mais_campos=("concluida_em", "responsavel"),
        )
        km = int(travada.km or 0)  # conferido nas pendências
        if km != veiculo.km_atual:
            veiculos.atualizar_km(veiculo, km, origem=_origem(travada, locacao))
        # A saída nova ativa a locação (fora de `aguardando_retirada`: 409). A correção só
        # acerta o km da saída enquanto a locação ainda aguarda a retirada.
        if saida and (
            travada.substitui_id is None or locacao.status == StatusLocacao.AGUARDANDO_RETIRADA
        ):
            locacoes.registrar_vistoria_saida(locacao, km=km, concluida_em=agora)
    _recarregar(vistoria)
    return vistoria


# --- Corrigir (VIS-04) ---


def corrigir(vistoria: Vistoria, motivo: str, usuario: Any) -> tuple[Vistoria, bool]:
    """Uma vistoria nova em `rascunho`, com os dados da concluída copiados e `substitui`
    apontando para ela. Se a correção já está aberta, devolve ela (`criada = False`)."""
    texto = (motivo or "").strip()
    if not texto:
        raise ErroDeValidacao({"motivo": ["Informe o motivo da correção."]})
    with transaction.atomic():
        travada = _travar(vistoria)
        if travada.status != S.CONCLUIDA or not travada.vigente:
            raise Conflito(
                "vistoria_nao_corrigivel", "Só a vistoria concluída e vigente pode ser corrigida."
            )
        aberta = Vistoria.objects.filter(substitui=travada, status=S.RASCUNHO).first()
        if aberta is not None:
            return aberta, False
        nova = Vistoria.objects.create(
            locacao_id=travada.locacao_id,
            veiculo_id=travada.veiculo_id,
            tipo=travada.tipo,
            km=travada.km,
            combustivel=travada.combustivel,
            itens=travada.itens,
            observacoes=travada.observacoes,
            responsavel_id=_quem(usuario),
            substitui=travada,
            motivo_correcao=texto,
        )
        fotos: dict[int, FotoVistoria] = {}
        for foto in FotoVistoria.ativos.filter(vistoria=travada):
            copia = FotoVistoria(
                vistoria=nova, posicao=foto.posicao, tirada_em=foto.tirada_em, por_id=foto.por_id
            )
            copia.arquivo.name = foto.arquivo.name  # o mesmo arquivo; nada é apagado
            copia.save()
            fotos[foto.pk] = copia
        for avaria in Avaria.objects.filter(vistoria=travada):
            Avaria.objects.create(
                vistoria=nova,
                veiculo_id=avaria.veiculo_id,
                descricao=avaria.descricao,
                preexistente=avaria.preexistente,
                valor_centavos=avaria.valor_centavos,
                vai_para_oficina=avaria.vai_para_oficina,
                foto=fotos.get(avaria.foto_id) if avaria.foto_id else None,
            )
        registrar_evento(
            "vistoria.corrigir",
            Categoria.OPERACAO,
            objeto=nova,
            depois=retrato(nova),
            motivo=texto,
            regra="VIS-04",
        )
    return nova, True


# --- Devolução e acerto (DEV-01 a DEV-06, LOC-09 a LOC-13) ---

D = StatusDevolucao
T = TipoItemAcerto
# A conta que cada cobrança vira ao encerrar, paga com a caução (DEV-02).
TIPO_DA_CONTA: dict[str, str] = {
    T.COMBUSTIVEL: TipoConta.ACERTO,
    T.AVARIA: TipoConta.AVARIA,
    T.ATRASO: TipoConta.ACERTO,
    T.KM_EXCEDENTE: TipoConta.ACERTO,
    T.MULTA_TRANSITO: TipoConta.MULTA,
    T.MULTA_ENCERRAMENTO: TipoConta.MULTA,
    # LOC-13: no mensal em 4 semanais, as semanas menos as parcelas canceladas podem ser cobrança.
    T.SEMANAS_NAO_USADAS: TipoConta.ACERTO,
}
# Os itens que a pessoa inclui; os outros saem da vistoria e da locação.
INCLUIDOS_PELA_PESSOA = (T.AVARIA, T.MULTA_TRANSITO)
CALCULADOS = (
    T.COMBUSTIVEL,
    T.ATRASO,
    T.KM_EXCEDENTE,
    T.PARCELA_ABERTA,
    T.MULTA_ENCERRAMENTO,
    T.SEMANAS_NAO_USADAS,
    T.DIAS_NAO_USADOS,
)
ABERTAS = (StatusLocacao.ATIVA, StatusLocacao.DEVOLUCAO_ATRASADA)


@dataclass(frozen=True)
class Calculado:
    tipo: str
    descricao: str
    valor_centavos: int
    modo: str = ModoItem.CALCULADO
    natureza: str = NaturezaItem.COBRANCA
    conta_id: int | None = None


def iniciar_devolucao(locacao: Locacao, usuario: Any) -> tuple[Devolucao, bool]:
    """A devolução da locação, com a vistoria de chegada e o acerto em `rascunho`. Se já existe,
    volta ela (`criada = False`): quem vistoria continua de onde parou (DEV-05)."""
    existente = Devolucao.objects.filter(locacao=locacao).first()
    if existente is not None:
        return existente, False
    if locacao.status not in ABERTAS:
        raise TransicaoInvalida(
            "transicao_locacao",
            "A devolução é só para locação ativa ou com a devolução atrasada.",
            {"status": locacao.status},
        )
    try:
        with transaction.atomic():
            chegada, _ = criar(locacao, TipoVistoria.DEVOLUCAO, usuario)
            antecipado = locacao.encerramento_antecipado_aprovado_em is not None
            devolucao = Devolucao.objects.create(
                locacao=locacao,
                vistoria=chegada,
                forma_devolucao=locacao.cancelamento_forma if antecipado else "",
            )
            registrar_evento(
                "devolucao.iniciar",
                Categoria.OPERACAO,
                objeto=devolucao,
                depois=retrato(devolucao),
            )
    except IntegrityError:  # outra pessoa abriu a devolução ao mesmo tempo
        concorrente = Devolucao.objects.filter(locacao=locacao).first()
        if concorrente is None:
            raise
        return concorrente, False
    recalcular(devolucao)
    return devolucao, True


def _chegadas(devolucao: Devolucao) -> Any:
    return Vistoria.objects.filter(
        locacao_id=devolucao.locacao_id,
        veiculo_id=devolucao.vistoria.veiculo_id,
        tipo=TipoVistoria.DEVOLUCAO,
    )


def chegada_vigente(devolucao: Devolucao) -> Vistoria | None:
    """A vistoria de chegada concluída que vale (a correção concluída substitui a anterior)."""
    vigente: Vistoria | None = _chegadas(devolucao).filter(status=S.CONCLUIDA, vigente=True).first()
    return vigente


def chegada_atual(devolucao: Devolucao) -> Vistoria:
    """A que está sendo preenchida (rascunho, inclusive uma correção) ou, sem ela, a vigente."""
    rascunho: Vistoria | None = _chegadas(devolucao).filter(status=S.RASCUNHO).first()
    return rascunho or chegada_vigente(devolucao) or devolucao.vistoria


def saida_vigente(locacao_id: int, veiculo_id: int) -> Vistoria | None:
    """A saída do mesmo veículo na mesma locação (com troca, a do trecho atual)."""
    saida: Vistoria | None = Vistoria.objects.filter(
        locacao_id=locacao_id,
        veiculo_id=veiculo_id,
        tipo=TipoVistoria.SAIDA,
        status=S.CONCLUIDA,
        vigente=True,
    ).first()
    return saida


def momento_da_devolucao(chegada: Vistoria) -> datetime:
    """O atraso é calculado na conclusão da vistoria de chegada (LOC-10, LOC-11); antes dela,
    a prévia usa a hora atual."""
    return chegada.concluida_em or relogio.agora()


def caucao_paga(locacao: Locacao) -> int:
    """A caução que o cliente pagou na locação: é dela que o acerto desconta (DEV-02)."""
    contas = financeiro_selectors.contas_da_origem(locacoes.ORIGEM, locacao.pk)
    return sum(
        c.valor_centavos for c in contas.filter(tipo=TipoConta.CAUCAO, status=StatusConta.PAGA)
    )


def _plural(n: int, singular: str, plural: str) -> str:
    return f"{n} {singular if n == 1 else plural}"


def calculados(locacao: Locacao, chegada: Vistoria) -> list[Calculado]:
    """Os itens que o sistema calcula (DEV-01, LOC-10, LOC-12, LOC-13)."""
    veiculo = chegada.veiculo
    saida = saida_vigente(locacao.pk, veiculo.pk)
    combustivel = conta.combustivel(
        capacidade_litros=veiculo.capacidade_tanque_litros,
        preco_litro_centavos=locacao.filial.preco_litro_centavos,
        saida=saida.combustivel if saida is not None else "",
        chegada=chegada.combustivel,
    )
    momento = momento_da_devolucao(chegada)
    atraso = locacoes.calcular_atraso(locacao, momento)
    dias = atraso["dias"]
    itens = [
        Calculado(
            T.COMBUSTIVEL,
            combustivel.descricao,
            combustivel.valor_centavos,
            ModoItem.CALCULADO if combustivel.calculado else ModoItem.INFORMADO,
        ),
        Calculado(
            T.ATRASO,
            "Atraso" if dias == 0 else f"Atraso ({_plural(dias, 'diária', 'diárias')})",
            atraso["valor_centavos"],
        ),
        Calculado(T.KM_EXCEDENTE, "Km excedente (plano com km livre)", 0),
    ]
    dia = locacoes.data_local(momento, locacao.filial)
    for parcela in financeiro_selectors.contas_da_origem(locacoes.ORIGEM, locacao.pk).filter(
        tipo=TipoConta.PARCELA, status=StatusConta.ABERTA, vencimento__lt=dia
    ):
        numero = f"Parcela {parcela.numero_parcela}"
        if parcela.total_parcelas:
            numero += f" de {parcela.total_parcelas}"
        itens.append(
            Calculado(
                T.PARCELA_ABERTA,
                f"{numero} · venceu em {parcela.vencimento.strftime('%d/%m')}",
                parcela.valor_centavos + parcela.multa_centavos + parcela.juros_centavos,
                conta_id=parcela.pk,
            )
        )
    if locacao.encerramento_antecipado_aprovado_em is not None:
        itens.append(
            Calculado(
                T.MULTA_ENCERRAMENTO,
                "Multa do encerramento antecipado",
                locacao.multa_encerramento_centavos or 0,
            )
        )
        # LOC-12: a diária conta pela hora real da devolução. LOC-13: no mensal em 4 semanais,
        # o crédito menos as parcelas canceladas pode ficar negativo e vira cobrança.
        credito = locacoes.credito_do_encerramento(locacao, momento)
        if credito.valor_centavos != 0:
            mensal = locacao.periodicidade == Periodicidade.MENSAL
            itens.append(
                Calculado(
                    T.SEMANAS_NAO_USADAS if mensal else T.DIAS_NAO_USADOS,
                    credito.descricao,
                    abs(credito.valor_centavos),
                    natureza=(
                        NaturezaItem.CREDITO
                        if credito.valor_centavos > 0
                        else NaturezaItem.COBRANCA
                    ),
                )
            )
    return itens


def _sincronizar(devolucao: Devolucao, chegada: Vistoria, novos: list[Calculado]) -> None:
    """Refaz os itens calculados e um item por avaria nova da chegada. O valor que a pessoa deu
    num item `informado` fica. Enquanto o acerto é rascunho, item que deixou de existir sai."""
    existentes = list(devolucao.itens.all())
    por_chave = {(i.tipo, i.conta_id): i for i in existentes if i.tipo in CALCULADOS}
    vistos = set()
    for novo in novos:
        chave = (novo.tipo, novo.conta_id)
        vistos.add(chave)
        item = por_chave.get(chave)
        if item is None:
            ItemAcerto.objects.create(
                devolucao=devolucao,
                tipo=novo.tipo,
                natureza=novo.natureza,
                modo=novo.modo,
                descricao=novo.descricao,
                valor_centavos=novo.valor_centavos,
                conta_id=novo.conta_id,
            )
            continue
        valor = novo.valor_centavos
        if novo.modo == ModoItem.INFORMADO:  # o combustível sem conta: vale o que foi informado
            valor = item.valor_centavos if item.modo == ModoItem.INFORMADO else 0
        atual = (item.modo, item.natureza, item.descricao, item.valor_centavos)
        if atual != (novo.modo, novo.natureza, novo.descricao, valor):
            item.modo, item.natureza, item.descricao = novo.modo, novo.natureza, novo.descricao
            item.valor_centavos = valor
            item.save()
    for chave, item in por_chave.items():
        if chave not in vistos:
            item.delete()

    avarias = {a.pk: a for a in Avaria.objects.filter(vistoria=chegada, preexistente=False)}
    com_item = {i.avaria_id: i for i in existentes if i.avaria_id is not None}
    for avaria in avarias.values():
        if avaria.pk not in com_item:
            ItemAcerto.objects.create(
                devolucao=devolucao,
                tipo=T.AVARIA,
                modo=ModoItem.INFORMADO,
                descricao=avaria.descricao,
                valor_centavos=avaria.valor_centavos or 0,
                avaria=avaria,
            )
    for avaria_id, item in com_item.items():
        if avaria_id not in avarias:
            item.delete()


def somas(itens: list[ItemAcerto]) -> tuple[int, int]:
    """`(cobranças, créditos)` em centavos."""
    cobrancas = sum(i.valor_centavos for i in itens if i.natureza == NaturezaItem.COBRANCA)
    creditos = sum(i.valor_centavos for i in itens if i.natureza == NaturezaItem.CREDITO)
    return cobrancas, creditos


def _travar_devolucao(devolucao: Devolucao) -> Devolucao:
    travada: Devolucao = (
        Devolucao.objects.select_for_update(of=("self",))
        .select_related("vistoria")
        .get(pk=devolucao.pk)
    )
    return travada


def _recarregar_devolucao(devolucao: Devolucao) -> None:
    devolucao.refresh_from_db()
    devolucao._status_salvo = devolucao.status


def recalcular(devolucao: Devolucao) -> Devolucao:
    """O acerto em rascunho é refeito a cada leitura e a cada mudança (contrato). Concluído, não
    muda mais."""
    with transaction.atomic():
        travada = _travar_devolucao(devolucao)
        if travada.status != D.RASCUNHO:
            return devolucao
        locacao = Locacao.objects.select_related("filial").get(pk=travada.locacao_id)
        chegada = chegada_atual(travada)
        _sincronizar(travada, chegada, calculados(locacao, chegada))
        cobrancas, creditos = somas(list(travada.itens.all()))
        caucao = caucao_paga(locacao)
        novo = (chegada.pk, caucao, caucao + creditos - cobrancas)
        if (travada.vistoria_id, travada.caucao_centavos, travada.saldo_centavos) != novo:
            travada.vistoria_id, travada.caucao_centavos, travada.saldo_centavos = novo
            travada.save(
                update_fields=["vistoria", "caucao_centavos", "saldo_centavos", "atualizado_em"]
            )
    _recarregar_devolucao(devolucao)
    return devolucao


def acerto_concluido() -> Conflito:
    return Conflito("acerto_concluido", "O acerto já foi encerrado e não se edita mais.")


def _acerto_em_rascunho(devolucao: Devolucao) -> Devolucao:
    travada = _travar_devolucao(devolucao)
    if travada.status != D.RASCUNHO:
        raise acerto_concluido()
    return travada


def item_calculado() -> Conflito:
    return Conflito("item_calculado", "Este item é calculado pelo sistema e não se edita.")


def _item(devolucao: Devolucao, item_id: int) -> ItemAcerto:
    item: ItemAcerto | None = devolucao.itens.filter(pk=item_id).first()
    if item is None:
        raise NaoEncontrado("item_nao_encontrado", "Este item não é deste acerto.")
    return item


def incluir_item(devolucao: Devolucao, dados: dict[str, Any]) -> ItemAcerto:
    """Avaria (tabela de peças ou orçamento) ou multa de trânsito já identificada (DEV-01)."""
    if dados["tipo"] not in INCLUIDOS_PELA_PESSOA:
        raise ErroDeValidacao(
            {"tipo": ["Inclua avaria ou multa de trânsito. Os outros itens são calculados."]}
        )
    with transaction.atomic():
        travada = _acerto_em_rascunho(devolucao)
        item = ItemAcerto(
            devolucao=travada,
            tipo=dados["tipo"],
            modo=ModoItem.INFORMADO,
            descricao=dados["descricao"].strip(),
            valor_centavos=dados["valor_centavos"],
        )
        with auditar(item, "acerto.incluir_item", Categoria.FINANCEIRO, regra="DEV-01"):
            item.save()
    recalcular(devolucao)
    return item


def editar_item(devolucao: Devolucao, item_id: int, dados: dict[str, Any]) -> ItemAcerto:
    """Só itens `informado`; os calculados respondem 409 `item_calculado`."""
    with transaction.atomic():
        travada = _acerto_em_rascunho(devolucao)
        item = _item(travada, item_id)
        if item.modo == ModoItem.CALCULADO:
            raise item_calculado()
        with auditar(item, "acerto.editar_item", Categoria.FINANCEIRO, regra="DEV-01"):
            if "valor_centavos" in dados:
                item.valor_centavos = dados["valor_centavos"]
            if dados.get("descricao"):
                item.descricao = dados["descricao"].strip()
            item.save()
    recalcular(devolucao)
    return item


def remover_item(devolucao: Devolucao, item_id: int) -> None:
    """Só os itens incluídos pela pessoa. O da avaria sai removendo a avaria na vistoria."""
    with transaction.atomic():
        travada = _acerto_em_rascunho(devolucao)
        item = _item(travada, item_id)
        if item.modo == ModoItem.CALCULADO:
            raise item_calculado()
        if item.avaria_id is not None or item.tipo == T.COMBUSTIVEL:
            raise Conflito(
                "item_da_vistoria",
                "Este item vem da vistoria de chegada. Corrija o valor ou remova a avaria lá.",
            )
        registrar_evento(
            "acerto.remover_item",
            Categoria.FINANCEIRO,
            objeto=item,
            antes=retrato(item),
            regra="DEV-01",
        )
        item.delete()
    recalcular(devolucao)


def definir_forma(devolucao: Devolucao, forma: str) -> Devolucao:
    """Como o saldo volta ao cliente: Pix, dinheiro ou estorno no cartão (DEV-02)."""
    with transaction.atomic():
        travada = _acerto_em_rascunho(devolucao)
        with auditar(travada, "acerto.forma_devolucao", Categoria.FINANCEIRO, regra="DEV-02"):
            travada.forma_devolucao = forma
            travada.save(update_fields=["forma_devolucao", "atualizado_em"])
    return recalcular(devolucao)


def vistoria_pendente() -> ErroDeRegra:
    return ErroDeRegra(
        "vistoria_pendente", "Conclua a vistoria de chegada antes de encerrar a devolução."
    )


def _liberar_veiculo(chegada: Vistoria, locacao: Locacao) -> list[int]:
    """DEV-04: avaria marcada "vai para oficina" leva o veículo a `em_manutencao` (a OS fica com
    o app `manutencao`, pelo evento `vistorias.devolucao_encerrada`); sem isso, `disponivel`.
    O km da chegada já entrou na conclusão da vistoria (VEI-02)."""
    oficina = list(
        Avaria.objects.filter(
            vistoria=chegada, preexistente=False, vai_para_oficina=True
        ).values_list("pk", flat=True)
    )
    veiculo = Veiculo.objects.get(pk=chegada.veiculo_id)
    if chegada.km is not None and chegada.km > veiculo.km_atual:
        veiculos.atualizar_km(veiculo, chegada.km, origem=_origem(chegada, locacao))
    if veiculo.status == StatusVeiculo.ALUGADO:
        destino = StatusVeiculo.EM_MANUTENCAO if oficina else StatusVeiculo.DISPONIVEL
        veiculos.transicionar(
            veiculo,
            destino,
            origem=_origem(chegada, locacao),
            motivo=(
                f"Avaria na devolução da {locacao.codigo} vai para a oficina"
                if oficina
                else f"Devolução da {locacao.codigo}"
            ),
        )
    return oficina


def encerrar_devolucao(devolucao: Devolucao, usuario: Any) -> Devolucao:
    """DEV-06, numa transação: acerto congelado; cobranças pagas com a caução; saldo positivo
    vira reembolso pela forma escolhida, e o negativo, conta a receber em 3 dias (DEV-02);
    locação `encerrada` (ou `cancelada` no encerramento antecipado, LOC-12) com `devolvida_em`
    pela LOC-11; veículo `disponivel` ou `em_manutencao` (DEV-04). Depois do commit, o recibo
    em PDF sai por WhatsApp."""
    with transaction.atomic():
        travada = _acerto_em_rascunho(devolucao)
        chegada = chegada_vigente(travada)
        if chegada is None or chegada.concluida_em is None:
            raise vistoria_pendente()
        recalcular(travada)
        locacao = Locacao.objects.select_related("filial").get(pk=travada.locacao_id)
        itens = list(travada.itens.all())
        cobrancas, creditos = somas(itens)
        saldo = travada.caucao_centavos + creditos - cobrancas
        forma = travada.forma_devolucao
        if saldo > 0 and not forma:
            raise ErroDeValidacao(
                {"forma_devolucao": ["Escolha como devolver: Pix, dinheiro ou estorno no cartão."]}
            )
        agora = relogio.agora()
        considerada = locacoes.calcular_atraso(locacao, chegada.concluida_em)
        devolvida_em: datetime = considerada["devolucao_considerada_em"]
        origem = financeiro.Origem("devolucao", travada.pk, locacao.codigo)
        cobrar = [i for i in itens if i.natureza == NaturezaItem.COBRANCA]
        financeiro.pagar_com_caucao(
            origem,
            filial_id=locacao.filial_id,
            cliente_id=locacao.cliente_id,
            disponivel_centavos=travada.caucao_centavos + creditos,
            abertas=list(
                ContaReceber.objects.filter(
                    pk__in=[i.conta_id for i in cobrar if i.conta_id is not None]
                ).order_by("vencimento", "id")
            ),
            cobrancas=[
                financeiro.Cobranca(TIPO_DA_CONTA[i.tipo], i.valor_centavos, i.descricao[:150])
                for i in cobrar
                if i.conta_id is None and i.valor_centavos > 0
            ],
            vencimento_do_saldo=locacoes.data_local(agora, locacao.filial)
            + timedelta(days=conta.DIAS_PARA_PAGAR_O_SALDO),
        )
        if saldo > 0:
            financeiro.devolver_ao_cliente(
                origem,
                filial_id=locacao.filial_id,
                cliente_id=locacao.cliente_id,
                valor_centavos=saldo,
                forma=forma,
                motivo=f"Devolução da caução da {locacao.codigo}",
                regra="DEV-02",
            )
        locacoes.encerrar(locacao, devolvida_em=devolvida_em)
        oficina = _liberar_veiculo(chegada, locacao)
        travada.saldo_centavos = saldo
        travada.preco_litro_centavos = locacao.filial.preco_litro_centavos
        travada.devolvida_em = devolvida_em
        travada.concluida_em = agora
        travada.encerrada_por_id = _quem(usuario)
        estados.transicionar(
            travada,
            D.CONCLUIDA,
            acao="devolucao.encerrar",
            regra="DEV-06",
            mais_campos=(
                "saldo_centavos",
                "preco_litro_centavos",
                "devolvida_em",
                "concluida_em",
                "encerrada_por",
            ),
        )
        publicar(
            "vistorias.devolucao_encerrada",
            devolucao_id=travada.pk,
            locacao_id=locacao.pk,
            veiculo_id=chegada.veiculo_id,
            avarias_para_oficina=oficina,
        )
        _agendar_recibo(travada.pk)
    _recarregar_devolucao(devolucao)
    return devolucao


# --- Recibo (DEV-06, AUD-05) ---


def _agendar_recibo(devolucao_id: int, reenviar: bool = False) -> None:
    from .tasks import vistorias_enviar_recibo

    schema = schema_atual()
    transaction.on_commit(lambda: vistorias_enviar_recibo.delay(schema, devolucao_id, reenviar))


def recibo_em_rascunho() -> Conflito:
    return Conflito("devolucao_em_rascunho", "O recibo sai quando a devolução é encerrada.")


def gravar_recibo(devolucao: Devolucao) -> None:
    """O PDF com a marca da locadora e as fotos da chegada, no armazenamento privado."""
    from . import recibo

    conteudo = recibo.pdf_do_recibo(devolucao)
    devolucao.recibo.save(
        f"{devolucao.locacao.codigo}-devolucao.pdf", ContentFile(conteudo), save=False
    )
    devolucao.save(update_fields=["recibo", "atualizado_em"])


def url_do_recibo(devolucao: Devolucao) -> arquivos.UrlAssinada:
    """URL de 15 minutos (AUD-05). Sem o PDF ainda (a tarefa não rodou), gera agora."""
    if devolucao.status != D.CONCLUIDA:
        raise recibo_em_rascunho()
    if not devolucao.recibo:
        with transaction.atomic():
            travada = _travar_devolucao(devolucao)
            if not travada.recibo:
                gravar_recibo(travada)
        devolucao.refresh_from_db()
    return arquivos.url_assinada(devolucao.recibo.name)


def reenviar_recibo(devolucao: Devolucao) -> None:
    if devolucao.status != D.CONCLUIDA:
        raise recibo_em_rascunho()
    _agendar_recibo(devolucao.pk, reenviar=True)


def marcar_recibo_enviado(devolucao: Devolucao) -> None:
    devolucao.recibo_enviado_em = relogio.agora()
    devolucao.save(update_fields=["recibo_enviado_em", "atualizado_em"])


def texto_do_saldo(devolucao: Devolucao) -> str:
    """A frase do saldo no recibo e no WhatsApp (DEV-02)."""
    saldo = devolucao.saldo_centavos
    if saldo > 0:
        como = {
            "pix": "por Pix em até 1 dia útil",
            "estorno_cartao": "por estorno no cartão",
            "dinheiro": "em dinheiro",
        }[devolucao.forma_devolucao]
        return f"Devolução de {formatar_reais(saldo)} {como}."
    if saldo < 0:
        dia = devolucao.concluida_em or relogio.agora()
        vence = locacoes.data_local(dia, devolucao.locacao.filial) + timedelta(
            days=conta.DIAS_PARA_PAGAR_O_SALDO
        )
        return f"Saldo de {formatar_reais(-saldo)} a pagar até {vence.strftime('%d/%m/%Y')}."
    return "A caução cobriu as cobranças."
