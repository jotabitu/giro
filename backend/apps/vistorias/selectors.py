"""Consultas de vistorias: a representação, as avarias abertas e a agenda (VIS-05)."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from django.db.models import Count, Q, QuerySet

from apps.clientes import selectors as clientes_selectors
from apps.filiais.models import Filial
from apps.financeiro import selectors as financeiro_selectors
from apps.financeiro.models import StatusConta
from apps.locacoes.models import Locacao, StatusLocacao
from apps.veiculos.models import Veiculo
from comum import arquivos, relogio

from . import acerto, services
from .models import (
    POSICOES_OBRIGATORIAS,
    Avaria,
    Combustivel,
    Devolucao,
    FotoVistoria,
    ItemAcerto,
    NaturezaItem,
    StatusDevolucao,
    StatusVistoria,
    TipoItemAcerto,
    TipoVistoria,
    Vistoria,
)

S = StatusVistoria
ORIGEM_PREEXISTENTE = "Registrado na vistoria anterior; não será cobrado do cliente na devolução."
ORIGEM_SAIDA = "Registrado nesta vistoria; não será cobrado do cliente na devolução."
SITUACAO_CNH = {
    "valida": "válida",
    "vencida": "vencida",
    "vencida_impede": "vencida há mais de 30 dias",
}
DIAS_DA_SEMANA = ("Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo")
MESES = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")


def base() -> QuerySet[Vistoria]:
    return Vistoria.objects.select_related(
        "locacao", "locacao__cliente", "locacao__filial", "veiculo", "responsavel"
    )


def sem_valores(dados: Any) -> Any:
    """Vistoriador: nenhum campo `_centavos` e nenhum bloco `acerto` (CA-016-07). Aplicado
    depois do serializer, que preencheria com `null` o campo que falta."""
    if isinstance(dados, dict):
        return {
            chave: sem_valores(valor)
            for chave, valor in dados.items()
            if not chave.endswith("_centavos") and chave != "acerto"
        }
    if isinstance(dados, list):
        return [sem_valores(item) for item in dados]
    return dados


# --- Representação ---


def _veiculo(veiculo: Veiculo) -> dict[str, Any]:
    return {
        "id": veiculo.pk,
        "placa": veiculo.placa,
        "modelo": f"{veiculo.marca} {veiculo.modelo}",
        "ano": veiculo.ano_modelo,
    }


def _cnh(locacao: Locacao) -> str | None:
    cliente = locacao.cliente
    situacao = clientes_selectors.situacao_da_cnh(cliente.cnh_validade, relogio.hoje())
    if not cliente.cnh_categoria or situacao is None:
        return None
    return f"Categoria {cliente.cnh_categoria} · {SITUACAO_CNH[situacao]}"


def representacao_foto(foto: FotoVistoria) -> dict[str, Any]:
    assinada = arquivos.url_assinada(foto.arquivo.name)
    return {
        "id": foto.pk,
        "posicao": foto.posicao,
        "tirada_em": foto.tirada_em,
        "url": assinada.url,
        "url_expira_em": assinada.expira_em,
    }


def avarias_abertas() -> QuerySet[Avaria]:
    """Registradas numa vistoria concluída e vigente, e ainda não reparadas."""
    return Avaria.objects.filter(
        resolvida_em__isnull=True, vistoria__status=S.CONCLUIDA, vistoria__vigente=True
    )


def _avaria(avaria: Avaria, origem: str | None, preexistente: bool) -> dict[str, Any]:
    return {
        "id": avaria.pk,
        "descricao": avaria.descricao,
        "preexistente": preexistente,
        "foto_id": avaria.foto_id,
        "vai_para_oficina": avaria.vai_para_oficina,
        "valor_centavos": avaria.valor_centavos,
        "origem": origem,
    }


def representacao_avaria(avaria: Avaria) -> dict[str, Any]:
    """A avaria que acabou de ser marcada nesta vistoria."""
    origem = ORIGEM_SAIDA if avaria.preexistente else None
    return _avaria(avaria, origem, avaria.preexistente)


def _avarias(vistoria: Vistoria) -> list[dict[str, Any]]:
    """As do veículo que já estavam abertas (preexistentes, não se cobram) e as desta vistoria.
    A correção não repete as da vistoria que ela substitui."""
    anteriores = (
        avarias_abertas()
        .filter(veiculo_id=vistoria.veiculo_id)
        .exclude(vistoria_id__in=[vistoria.pk, vistoria.substitui_id or 0])
    )
    if vistoria.status == S.CONCLUIDA:  # as abertas antes dela, não as de depois
        anteriores = anteriores.filter(vistoria__concluida_em__lt=vistoria.concluida_em)
    proprias = Avaria.objects.filter(vistoria=vistoria)
    saida = vistoria.tipo == TipoVistoria.SAIDA
    return [_avaria(a, ORIGEM_PREEXISTENTE, True) for a in anteriores.order_by("id")] + [
        _avaria(a, ORIGEM_SAIDA if saida else None, a.preexistente) for a in proprias
    ]


def _resumo_locacao(locacao: Locacao) -> dict[str, Any]:
    caucao_paga = (
        financeiro_selectors.contas_da_origem("locacao", locacao.pk)
        .filter(tipo="caucao", status=StatusConta.PAGA)
        .exists()
    )
    return {
        "periodicidade": locacao.periodicidade,
        "inicio": locacao.inicio,
        "fim_previsto": locacao.fim_previsto,
        "km_livre": True,  # todos os planos têm km livre (DEV-01)
        "diaria_centavos": locacao.diaria_centavos,
        "caucao_centavos": locacao.caucao_centavos,
        "caucao_paga": caucao_paga,
    }


def representacao(vistoria: Vistoria) -> dict[str, Any]:
    locacao = vistoria.locacao
    veiculo = vistoria.veiculo
    fotos = list(FotoVistoria.ativos.filter(vistoria=vistoria).order_by("id"))
    feitas = {f.posicao for f in fotos}
    faltam = [p for p in POSICOES_OBRIGATORIAS if p not in feitas]
    pendencias = (
        [p.curta for p in services.pendencias_da_vistoria(vistoria, veiculo)]
        if vistoria.status == S.RASCUNHO
        else []
    )
    responsavel = vistoria.responsavel
    return {
        "id": vistoria.pk,
        "tipo": vistoria.tipo,
        "status": vistoria.status,
        "locacao": {"id": locacao.pk, "codigo": locacao.codigo},
        "veiculo": _veiculo(veiculo),
        "cliente": {"nome": locacao.cliente.nome, "cnh": _cnh(locacao)},
        "km": vistoria.km,
        "km_ultima_leitura": {
            "km": veiculo.km_atual,
            "em": relogio.hoje()
            if veiculo.km_atualizado_em is None
            else veiculo.km_atualizado_em.astimezone(ZoneInfo(locacao.filial.fuso)).date(),
        },
        "combustivel": vistoria.combustivel or None,
        "fotos": [representacao_foto(f) for f in fotos],
        "fotos_obrigatorias": {
            "feitas": len(POSICOES_OBRIGATORIAS) - len(faltam),
            "total": len(POSICOES_OBRIGATORIAS),
            "faltam": faltam,
        },
        "itens": vistoria.itens,
        "avarias": _avarias(vistoria),
        "observacoes": vistoria.observacoes or None,
        "responsavel": {"id": responsavel.pk, "nome": responsavel.nome} if responsavel else None,
        "concluida_em": vistoria.concluida_em,
        "substitui": vistoria.substitui_id,
        "motivo_correcao": vistoria.motivo_correcao or None,
        "vigente": vistoria.vigente,
        "pendencias": pendencias,
        "pode_concluir": vistoria.status == S.RASCUNHO and not pendencias,
        "resumo_locacao": _resumo_locacao(locacao),
    }


# --- Avarias abertas (tela Vistoriador) ---


def avaria_aberta(avaria: Avaria) -> dict[str, Any]:
    veiculo = avaria.veiculo
    vistoria = avaria.vistoria
    return {
        "id": avaria.pk,
        "descricao": avaria.descricao,
        "veiculo": {
            "id": veiculo.pk,
            "placa": veiculo.placa,
            "modelo": f"{veiculo.marca} {veiculo.modelo}",
        },
        "locacao": {"id": vistoria.locacao_id, "codigo": vistoria.locacao.codigo},
        "registrada_em": vistoria.concluida_em,
        "foto": representacao_foto(avaria.foto) if avaria.foto is not None else None,
        "vai_para_oficina": avaria.vai_para_oficina,
        "valor_centavos": avaria.valor_centavos,
    }


# --- Agenda do vistoriador (VIS-05) ---


def _dias(dia: str, hoje: date) -> tuple[date, date]:
    if dia == "amanha":
        amanha = hoje + timedelta(days=1)
        return amanha, amanha
    if dia == "semana":
        return hoje, hoje + timedelta(days=6)
    return hoje, hoje


def _plural(quantos: int, singular: str, plural: str) -> str:
    return f"{quantos} {singular if quantos == 1 else plural}"


def _resumo(de: date, ate: date, saidas: int, devolucoes: int) -> str:
    if de == ate:
        quando = f"{DIAS_DA_SEMANA[de.weekday()]}, {de.day:02d} {MESES[de.month - 1]}"
    else:
        quando = f"{de.day:02d} a {ate.day:02d} {MESES[ate.month - 1]}"
    contagem = (
        f"{_plural(saidas, 'saída', 'saídas')} e {_plural(devolucoes, 'devolução', 'devoluções')}"
    )
    return f"{quando} · {contagem}"


SITUACOES = {
    "agendada": ("Agendada", "neutro"),
    "hoje": ("Hoje", "info"),
    "em_andamento": ("Em andamento", "aviso"),
    "atrasada": ("Atrasada", "perigo"),
    "concluida": ("Concluída", "sucesso"),
}
ACOES = {"iniciar": "Iniciar", "continuar": "Continuar", "abrir": "Abrir"}


def _situacao(
    vistoria: Vistoria | None, horario: datetime, agora: datetime, hoje: date, fuso: ZoneInfo
) -> str:
    if vistoria is not None and vistoria.status == S.CONCLUIDA:
        return "concluida"
    if vistoria is not None:
        return "em_andamento"
    if horario < agora:
        return "atrasada"
    return "hoje" if horario.astimezone(fuso).date() == hoje else "agendada"


def _vistorias_por_locacao(locacao_ids: list[int], tipo: str) -> dict[int, Vistoria]:
    """A vistoria em andamento ou a vigente de cada locação, do veículo atual."""
    por_locacao: dict[int, Vistoria] = {}
    for vistoria in (
        Vistoria.objects.filter(locacao_id__in=locacao_ids, tipo=tipo)
        .filter(Q(status=S.RASCUNHO) | Q(status=S.CONCLUIDA, vigente=True))  # sem as descartadas
        .select_related("locacao")
        .order_by("id")
    ):
        if vistoria.veiculo_id == vistoria.locacao.veiculo_id:
            por_locacao[vistoria.locacao_id] = vistoria  # o rascunho (mais novo) prevalece
    return por_locacao


def _item(
    tipo: str,
    locacao: Locacao,
    horario: datetime,
    vistoria: Vistoria | None,
    situacao: str,
) -> dict[str, Any]:
    veiculo = locacao.veiculo
    rotulo, tom = SITUACOES[situacao]
    if vistoria is not None and vistoria.status == S.RASCUNHO:
        acao = "continuar"
    elif tipo == TipoVistoria.SAIDA and vistoria is None:
        acao = "iniciar"
    else:
        acao = "abrir"
    return {
        "id": f"{tipo}-{locacao.numero}",
        "tipo": tipo,
        "horario": horario,
        "veiculo": {
            "id": veiculo.pk,
            "placa": veiculo.placa,
            "modelo": f"{veiculo.marca} {veiculo.modelo}",
        },
        "cliente": {"nome": locacao.cliente.nome},
        "locacao": {"id": locacao.pk, "codigo": locacao.codigo},
        "situacao": {"codigo": situacao, "rotulo": rotulo, "tom": tom},
        "vistoria_id": vistoria.pk if vistoria is not None else None,
        "acao": {"codigo": acao, "rotulo": ACOES[acao]},
    }


def agenda(filial: Filial, dia: str = "hoje") -> dict[str, Any]:
    """Retiradas das locações `aguardando_retirada` com início no período e devoluções previstas
    (fim previsto no período, ou `devolucao_atrasada`), da filial, em ordem de horário."""
    fuso = ZoneInfo(filial.fuso)
    agora = relogio.agora()
    hoje = agora.astimezone(fuso).date()
    de, ate = _dias(dia, hoje)
    inicio = datetime.combine(de, time.min, tzinfo=fuso)
    fim = datetime.combine(ate + timedelta(days=1), time.min, tzinfo=fuso)
    locacoes = Locacao.objects.filter(filial=filial).select_related("cliente", "veiculo")
    retiradas = list(
        locacoes.filter(
            status=StatusLocacao.AGUARDANDO_RETIRADA, inicio__gte=inicio, inicio__lt=fim
        )
    )
    previstas = Q(status=StatusLocacao.ATIVA, fim_previsto__gte=inicio, fim_previsto__lt=fim)
    if dia != "amanha":
        previstas |= Q(status=StatusLocacao.DEVOLUCAO_ATRASADA)
    devolucoes = list(locacoes.filter(previstas))
    saidas_feitas = _vistorias_por_locacao([x.pk for x in retiradas], TipoVistoria.SAIDA)
    chegadas = _vistorias_por_locacao([x.pk for x in devolucoes], TipoVistoria.DEVOLUCAO)

    itens = []
    for tipo, lista, vistorias, momento in (
        (TipoVistoria.SAIDA, retiradas, saidas_feitas, "inicio"),
        (TipoVistoria.DEVOLUCAO, devolucoes, chegadas, "fim_previsto"),
    ):
        for locacao in lista:
            horario = getattr(locacao, momento)
            vistoria = vistorias.get(locacao.pk)
            situacao = _situacao(vistoria, horario, agora, hoje, fuso)
            itens.append(_item(tipo, locacao, horario, vistoria, situacao))
    itens.sort(key=lambda i: (i["horario"], i["id"]))

    proxima = next(
        (i for i in itens if i["situacao"]["codigo"] != "concluida" and i["horario"] >= agora),
        None,
    )
    return {
        "resumo": _resumo(de, ate, len(retiradas), len(devolucoes)),
        "proxima": {
            "item_id": proxima["id"],
            "em_minutos": int((proxima["horario"] - agora).total_seconds() // 60),
        }
        if proxima
        else None,
        "avarias_abertas": avarias_abertas().filter(veiculo__filial=filial).count(),
        "resultados": itens,
    }


def concluidas_hoje_por_responsavel(filial: Filial) -> dict[int, int]:
    """Vistorias concluídas hoje na filial, por responsável: o resumo da equipe do gerente."""
    fuso = ZoneInfo(filial.fuso)
    comeco = datetime.combine(relogio.agora().astimezone(fuso).date(), time.min, tzinfo=fuso)
    return dict(
        Vistoria.objects.filter(
            locacao__filial=filial,
            status=S.CONCLUIDA,
            concluida_em__gte=comeco,
            concluida_em__lt=comeco + timedelta(days=1),
        )
        .order_by()
        .values_list("responsavel_id")
        .annotate(total=Count("id"))
        .values_list("responsavel_id", "total")
    )


# --- Devolução e acerto (DEV-01 a DEV-06) ---

NIVEL = dict(Combustivel.choices)


def _texto_km(rodou: int) -> str:
    return f"Rodou {rodou:,} km · plano com km livre".replace(",", ".")


def _situacao_do_item(item: dict[str, Any] | None) -> str | None:
    if item is None or item.get("ok") is None:
        return None
    return "ok" if item["ok"] else (item.get("observacao") or "com problema")


def comparacao(locacao: Locacao, chegada: Vistoria) -> dict[str, Any]:
    """Saída × chegada do mesmo veículo na mesma locação (com troca, a do trecho atual)."""
    saida = services.saida_vigente(locacao.pk, chegada.veiculo_id)
    km_saida = saida.km if saida is not None else None
    rodou = chegada.km - km_saida if chegada.km is not None and km_saida is not None else None
    combustivel = acerto.combustivel(
        capacidade_litros=chegada.veiculo.capacidade_tanque_litros,
        preco_litro_centavos=None,
        saida=saida.combustivel if saida is not None else "",
        chegada=chegada.combustivel,
    )
    capacidade = chegada.veiculo.capacidade_tanque_litros
    litros = (
        str((capacidade * combustivel.quartos / 4).quantize(Decimal("0.1")))
        if capacidade is not None
        else None
    )
    fotos_saida = (
        {f.posicao: f for f in FotoVistoria.ativos.filter(vistoria=saida)} if saida else {}
    )
    fotos_chegada = {f.posicao: f for f in FotoVistoria.ativos.filter(vistoria=chegada)}
    itens_saida = {i["codigo"]: i for i in (saida.itens if saida is not None else [])}
    return {
        "km": {
            "saida": km_saida,
            "agora": chegada.km,
            "rodou": rodou,
            "texto": _texto_km(rodou) if rodou is not None else "Plano com km livre",
        },
        "combustivel": {
            "saida": (saida.combustivel or None) if saida is not None else None,
            "agora": chegada.combustivel or None,
            "faltou": acerto.FALTOU.get(combustivel.quartos),
            "litros_faltantes": litros,
        },
        "fotos": [
            {
                "posicao": posicao,
                "saida": representacao_foto(fotos_saida[posicao])
                if posicao in fotos_saida
                else None,
                "agora": representacao_foto(fotos_chegada[posicao])
                if posicao in fotos_chegada
                else None,
            }
            for posicao in POSICOES_OBRIGATORIAS
        ],
        "itens": [
            {
                "codigo": item["codigo"],
                "rotulo": item["rotulo"],
                "saida": _situacao_do_item(itens_saida.get(item["codigo"])),
                "agora": _situacao_do_item(item),
                "novo": item.get("ok") is False
                and _situacao_do_item(itens_saida.get(item["codigo"])) in ("ok", None),
            }
            for item in chegada.itens
        ],
    }


def _item_do_acerto(item: ItemAcerto) -> dict[str, Any]:
    return {
        "id": item.pk,
        "tipo": item.tipo,
        "descricao": item.descricao,
        "valor_centavos": item.valor_centavos,
        "modo": item.modo,
        "avaria_id": item.avaria_id,
        "conta_id": item.conta_id,
    }


def representacao_acerto(devolucao: Devolucao, locacao: Locacao | None = None) -> dict[str, Any]:
    locacao = locacao or Locacao.objects.select_related("filial").get(pk=devolucao.locacao_id)
    itens = list(devolucao.itens.order_by("id"))
    cobrancas, creditos = services.somas(itens)
    resultado = acerto.resultado(devolucao.caucao_centavos, creditos, cobrancas)
    return {
        "status": "concluido" if devolucao.status == StatusDevolucao.CONCLUIDA else "rascunho",
        "caucao_centavos": devolucao.caucao_centavos,
        "itens": [_item_do_acerto(i) for i in itens if i.natureza == NaturezaItem.COBRANCA],
        "creditos": [_item_do_acerto(i) for i in itens if i.natureza == NaturezaItem.CREDITO],
        "total_cobrancas_centavos": cobrancas,
        "total_creditos_centavos": creditos,
        "saldo_centavos": devolucao.saldo_centavos,
        "resultado": {
            "tipo": resultado.tipo,
            "valor_centavos": resultado.valor_centavos,
            "texto": resultado.texto,
            "botao": resultado.botao,
        },
        "avisos": services.avisos_do_acerto(devolucao),
        # A escolha do acerto ou, sem ela, a do encerramento antecipado que vale (T-122).
        "forma_devolucao": services.forma_da_devolucao(devolucao, locacao) or None,
    }


def representacao_devolucao(devolucao: Devolucao) -> dict[str, Any]:
    locacao = Locacao.objects.select_related("cliente", "filial", "veiculo").get(
        pk=devolucao.locacao_id
    )
    atual = services.chegada_atual(devolucao)
    # Sem chegada (troca cancelada com a chegada descartada), `vistoria` e `comparacao` vêm
    # nulas até o veículo voltar (LOC-09, T-122).
    chegada = base().get(pk=atual.pk) if atual is not None else None
    veiculo = chegada.veiculo if chegada is not None else locacao.veiculo
    atraso = next((i for i in devolucao.itens.all() if i.tipo == TipoItemAcerto.ATRASO), None)
    return {
        "id": devolucao.pk,
        "status": devolucao.status,
        "locacao": {
            "id": locacao.pk,
            "codigo": locacao.codigo,
            "status": locacao.status,
            "cliente": locacao.cliente.nome,
            "veiculo": f"{veiculo.marca} {veiculo.modelo} · {veiculo.placa}",
            "no_horario": atraso is None or atraso.valor_centavos == 0,
        },
        "vistoria": representacao(chegada) if chegada is not None else None,
        "comparacao": comparacao(locacao, chegada) if chegada is not None else None,
        "acerto": representacao_acerto(devolucao, locacao),
        "devolvida_em": devolucao.devolvida_em,
        "concluida_em": devolucao.concluida_em,
        "recibo_enviado_em": devolucao.recibo_enviado_em,
    }
