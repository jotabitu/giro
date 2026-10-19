"""Números do painel: contadores do menu e o início por perfil (`docs/api/painel.md`; USR-05,
USR-07, USR-08, IMP-01, VEI-06, FIN-01, FIN-13, FIN-15, APR-09).

Só leitura, a partir dos `selectors` dos outros apps (ADR 0011, nível 13). Regra do MVP: um
número sai quando a fonte dele já existe no backend; senão, `null` (o bloco ou o KPI inteiro).
Nenhum número é estimado ou fixo. Caixa e despesas vêm do `financeiro` (T-017); manutenção,
vendas e conciliação ainda não existem e vêm `null`.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from zoneinfo import ZoneInfo

from django.conf import settings

from apps.aprovacoes import selectors as aprovacoes_selectors
from apps.clientes import selectors as clientes_selectors
from apps.contas import navegacao
from apps.contas import selectors as contas_selectors
from apps.contratos import selectors as contratos_selectors
from apps.empresas import selectors as empresas_selectors
from apps.filiais import selectors as filiais_selectors
from apps.filiais.models import Filial
from apps.financeiro import selectors as financeiro_selectors
from apps.locacoes import selectors as locacoes_selectors
from apps.plataforma import selectors as plataforma_selectors
from apps.veiculos import selectors as veiculos_selectors
from apps.vistorias import selectors as vistorias_selectors
from comum import relogio
from comum.dinheiro import formatar_reais

from . import configuracoes as textos_de_configuracoes

PERIODOS = {"hoje": 1, "7d": 7, "30d": 30}
PERIODO_PADRAO = "7d"
CONTEXTO_DO_PERIODO = {"hoje": "hoje", "7d": "últimos 7 dias", "30d": "últimos 30 dias"}
MESES = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")
ONLINE = timedelta(minutes=5)  # USR-08: "online" = sessão usada nos últimos 5 minutos
ITENS_DE_APROVACAO = 5
SEGMENTOS_DA_FROTA = (
    ("disponivel", "Disponível"),
    ("alugado", "Alugado"),
    ("reservado", "Reservado"),
    ("em_manutencao", "Manutenção"),
    ("a_venda", "À venda"),
)
# Passos obrigatórios da implantação (tabela "Implantação" das regras): a "Configuração
# inicial" do `Pos-Dashboard`. Marca, recebimentos e importação são opcionais.
PASSOS_DA_CONFIGURACAO = ("conta", "filial", "ramo", "precos", "contrato")
ROTULOS_DA_CONFIGURACAO = (
    ("marca", "Marca"),
    ("filial", "filial"),
    ("precos", "preços"),
    ("contrato", "contrato"),
)
FORMA_DO_REEMBOLSO = {"pix": "por Pix", "dinheiro": "em dinheiro", "estorno_cartao": "no cartão"}


@dataclass(frozen=True)
class Escopo:
    """Filiais do `X-Filial`, resolvidas na view por `filtrar_por_filial` (USR-07)."""

    filiais: frozenset[int]
    todas: bool

    @property
    def chave(self) -> str:
        return "todas" if self.todas else ",".join(str(pk) for pk in sorted(self.filiais))

    def filial(self) -> Filial | None:
        """A filial única do escopo (`None` com "Todas as filiais")."""
        if self.todas or len(self.filiais) != 1:
            return None
        return Filial.objects.get(pk=next(iter(self.filiais)))

    def lista(self) -> list[Filial]:
        return list(Filial.objects.filter(pk__in=self.filiais).order_by("-matriz", "nome"))


# --- Textos ---


def _plural(quantos: int, singular: str, plural: str) -> str:
    return f"{quantos} {singular if quantos == 1 else plural}"


def _pct_texto(valor: Decimal | str) -> str:
    """`"71.00"` vira `"71%"`; `"56.76"` vira `"56,76%"`."""
    numero = Decimal(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if numero == numero.to_integral_value():
        return f"{int(numero)}%"
    return f"{numero}%".replace(".", ",")


def _pct(parte: int, total: int) -> str:
    if not total:
        return "0.00"
    valor = Decimal(parte * 100) / Decimal(total)
    return str(valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _fuso(escopo: Escopo) -> ZoneInfo:
    filial = escopo.filial()
    return ZoneInfo(filial.fuso if filial is not None else settings.TIME_ZONE)


def saudacao(nome: str, fuso: ZoneInfo) -> str:
    hora = relogio.agora().astimezone(fuso).hour
    cumprimento = "Bom dia" if hora < 12 else "Boa tarde" if hora < 18 else "Boa noite"
    primeiro = locacoes_selectors.primeiro_nome(nome)
    return f"{cumprimento}, {primeiro}" if primeiro else cumprimento


def _ha_quanto(momento: datetime) -> str:
    minutos = max(0, int((relogio.agora() - momento).total_seconds() // 60))
    if minutos < 60:
        return f"há {minutos} min"
    if minutos < 24 * 60:
        return f"há {minutos // 60} h"
    return f"há {_plural(minutos // (24 * 60), 'dia', 'dias')}"


def _ultimo_acesso(momento: datetime | None, fuso: ZoneInfo) -> str:
    if momento is None:
        return "ainda não acessou"
    dia = momento.astimezone(fuso).date()
    hoje = relogio.agora().astimezone(fuso).date()
    if dia == hoje:
        return "último acesso hoje"
    if dia == hoje - timedelta(days=1):
        return "último acesso ontem"
    return f"último acesso em {dia.day:02d} {MESES[dia.month - 1]}"


def _kpi(
    chave: str,
    rotulo: str,
    tipo: str | None,
    valor: Any,
    contexto: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """KPI com valor tipado; `tipo` `None` = módulo que ainda não existe (`valor: null`)."""
    return {
        "chave": chave,
        "rotulo": rotulo,
        "valor": {"tipo": tipo, "valor": valor} if tipo is not None else None,
        "contexto": contexto,
        **extra,
    }


def _tendencia(diferenca: int) -> str | None:
    return "sobe" if diferenca > 0 else "desce" if diferenca < 0 else None


def _janela(dias: int, ate: date, fuso: ZoneInfo) -> tuple[datetime, datetime]:
    """Os últimos `dias` dias até `ate`, inclusive, no fuso."""
    comeco = datetime.combine(ate - timedelta(days=dias - 1), time.min, tzinfo=fuso)
    return comeco, datetime.combine(ate + timedelta(days=1), time.min, tzinfo=fuso)


# --- Contadores do menu ---


def _vendedor_id(usuario: Any) -> int | None:
    """USR-08: o vendedor vê só os números dele (`painel: proprios`)."""
    return usuario.pk if getattr(usuario, "perfil", "") == "vendedor" else None


def _agenda_pendente(escopo: Escopo) -> int:
    """VIS-05: vistorias do dia ainda não concluídas, somando as filiais do escopo."""
    return sum(
        1
        for filial in escopo.lista()
        for item in vistorias_selectors.agenda(filial, "hoje")["resultados"]
        if item["situacao"]["codigo"] != "concluida"
    )


def _aprovacoes_pendentes(usuario: Any, escopo: Escopo) -> Any:
    """Pedidos `pendente` que a pessoa decide, nas filiais do escopo, sem os dela (APR-09)."""
    quem = aprovacoes_selectors.decisor(usuario)
    return aprovacoes_selectors.filtrar(
        aprovacoes_selectors.que_decide(quem), status="pendente", tipo=None
    ).filter(filial_id__in=escopo.filiais)


PERFIS_QUE_APROVAM_DESPESA = frozenset({"administrador", "gerente"})  # APR-03

CONTADORES: dict[str, Callable[[Any, Escopo], int | None]] = {
    "veiculos": lambda u, e: veiculos_selectors.contagens(veiculos_selectors.da_frota(e.filiais))[
        "todos"
    ],
    "locacoes": lambda u, e: locacoes_selectors.por_aba(
        locacoes_selectors.das_filiais(e.filiais, _vendedor_id(u)), "abertas"
    ).count(),
    "aprovacoes": lambda u, e: _aprovacoes_pendentes(u, e).count(),
    "receber": lambda u, e: financeiro_selectors.atrasadas(e.filiais, relogio.hoje()).quantidade,
    # APR-03 e APR-09: quem não aprova despesa fica sem contador.
    "despesas": lambda u, e: (
        financeiro_selectors.despesas_para_aprovar(e.filiais, u.pk)
        if getattr(u, "perfil", "") in PERFIS_QUE_APROVAM_DESPESA
        else None
    ),
    "contas_a_pagar": lambda u, e: financeiro_selectors.despesas_a_pagar_vencendo(
        e.filiais, relogio.hoje()
    ).count(),
    "usuarios": lambda u, e: contas_selectors.convites_pendentes(),
    "agenda": lambda u, e: _agenda_pendente(e),
    "avarias": lambda u, e: (
        vistorias_selectors.avarias_abertas().filter(veiculo__filial_id__in=e.filiais).count()
    ),
}


def contadores(usuario: Any, escopo: Escopo, chaves: set[str]) -> dict[str, int | None]:
    """Só as chaves dos itens do menu da pessoa; sem fonte (manutenções, conciliação,
    propostas), `null`."""
    return {
        chave: (CONTADORES[chave](usuario, escopo) if chave in CONTADORES else None)
        for chave in sorted(chaves)
    }


# --- Início: blocos comuns ---


def _frota(escopo: Escopo) -> dict[str, int]:
    return veiculos_selectors.contagens(veiculos_selectors.da_frota(escopo.filiais))


def _alugados_agora(escopo: Escopo, contagem: dict[str, int]) -> dict[str, Any]:
    semana_passada = relogio.agora() - timedelta(days=7)
    diferenca = contagem["alugado"] - veiculos_selectors.alugados_em(escopo.filiais, semana_passada)
    contexto = None
    if diferenca:
        contexto = f"{abs(diferenca)} a {'mais' if diferenca > 0 else 'menos'} esta semana"
    return _kpi(
        "alugados_agora",
        "Alugados agora",
        "numero",
        contagem["alugado"],
        contexto,
        tendencia=_tendencia(diferenca),
    )


def _receita(escopo: Escopo, dias: int, ate: date, fuso: ZoneInfo) -> int:
    return financeiro_selectors.receita_de_locacao(escopo.filiais, *_janela(dias, ate, fuso))


# --- Variante `geral` (administrador, tela Main) ---


def _geral(usuario: Any, escopo: Escopo, periodo: str) -> dict[str, Any]:
    fuso = _fuso(escopo)
    hoje = relogio.hoje()
    locacoes = locacoes_selectors.das_filiais(escopo.filiais)
    precisam = locacoes_selectors.por_aba(locacoes, "precisam_acao").count()
    contagem = _frota(escopo)
    atraso = financeiro_selectors.atrasadas(escopo.filiais, hoje)
    ocupacao = veiculos_selectors.ocupacao_da_frota(escopo.filiais, PERIODOS[periodo])
    meta = empresas_selectors.meta_ocupacao_pct()
    devolucoes = locacoes_selectors.devolucoes_da_semana(locacoes)
    atrasadas = locacoes.filter(status="devolucao_atrasada").count()
    vencem = financeiro_selectors.vencem_entre(escopo.filiais, hoje, hoje + timedelta(days=1))
    itens = []
    if atrasadas:
        verbo = "está atrasada" if atrasadas == 1 else "estão atrasadas"
        itens.append(
            {
                "texto": f"{_plural(atrasadas, 'devolução', 'devoluções')} {verbo}",
                "gravidade": "critica",
                "destino": {"chave": "locacoes", "filtro": "aba=precisam_acao"},
            }
        )
    if vencem.quantidade:
        verbo = "vence" if vencem.quantidade == 1 else "vencem"
        itens.append(
            {
                "texto": f"{_plural(vencem.quantidade, 'parcela', 'parcelas')} {verbo} até amanhã",
                "gravidade": "info",
                "destino": {"chave": "receber", "filtro": "situacao=vencem_hoje"},
            }
        )
    return {
        "atencao": {
            "quantidade": precisam,
            "texto": (
                f"{_plural(precisam, 'contrato pede', 'contratos pedem')} atenção"
                if precisam
                else "Nenhum contrato pede atenção"
            ),
        },
        "kpis": [
            _kpi(
                "frota_ativa",
                "Frota ativa",
                "numero",
                contagem["todos"],
                f"{_plural(contagem['motos'], 'moto', 'motos')} · "
                f"{_plural(contagem['carros'], 'carro', 'carros')}",
                destaque=True,
            ),
            _alugados_agora(escopo, contagem),
            _kpi(
                "receita_locacao",
                "Receita de locação",
                "centavos",
                _receita(escopo, PERIODOS[periodo], hoje, fuso),
                CONTEXTO_DO_PERIODO[periodo],
            ),
            _kpi(
                "em_atraso",
                "Em atraso",
                "numero",
                atraso.clientes,
                f"{formatar_reais(atraso.centavos)} a receber",
            ),
        ],
        "frota": {
            "ocupacao_pct": ocupacao,
            "meta_ocupacao_pct": str(meta),
            "nota": f"ocupação de {_pct_texto(ocupacao)} · meta de {_pct_texto(meta)}",
            "segmentos": [
                {"status": status, "rotulo": rotulo, "quantidade": contagem[status]}
                for status, rotulo in SEGMENTOS_DA_FROTA
            ],
        },
        "devolucoes_semana": {
            "subtitulo": _plural(len(devolucoes), "contrato", "contratos"),
            "linhas": [locacoes_selectors.linha_do_painel(x) for x in devolucoes],
        },
        "pendencias": {
            "titulo": (
                f"{_plural(precisam, 'contrato precisa', 'contratos precisam')} de ação hoje"
                if precisam
                else "Nenhum contrato precisa de ação hoje"
            ),
            "itens": itens,
        },
        "caixa_hoje": _caixa_hoje(escopo),
    }


def _caixa_hoje(escopo: Escopo) -> dict[str, Any] | None:
    """O caixa de hoje da filial; `null` com "Todas as filiais" ou sem caixa hoje (FIN-07)."""
    filial = escopo.filial()
    if filial is None:
        return None
    return financeiro_selectors.caixa_hoje_do_painel(filial.pk, relogio.hoje())


# --- Variante `implantacao` (administrador antes da 1ª locação, tela Pos-Dashboard) ---


def _teste(empresa: Any) -> dict[str, Any] | None:
    teste = plataforma_selectors.assinatura(empresa)["teste"]
    if teste is None or teste["fim"] is None:
        return None
    fim, dias = teste["fim"], teste["dias_restantes"]
    return {
        "fim": fim,
        "dias_restantes": dias,
        "texto": (
            f"Seu teste grátis termina em {_plural(dias, 'dia', 'dias')} "
            f"({fim.day:02d} {MESES[fim.month - 1]})."
        ),
    }


def _primeiros_passos(empresa: Any, veiculos: int, convites: int) -> dict[str, Any]:
    passos = plataforma_selectors.passos_implantacao(empresa)
    feitos = [rotulo for passo, rotulo in ROTULOS_DA_CONFIGURACAO if passo in passos]
    partes = [*feitos, _plural(veiculos, "veículo cadastrado", "veículos cadastrados")]
    detalhe = ", ".join(partes[:-1]) + f" e {partes[-1]}" if len(partes) > 1 else partes[0]
    primeira = "primeira_locacao" in passos
    itens = [
        {
            "chave": "configuracao_inicial",
            "rotulo": "Configuração inicial",
            "detalhe": detalhe[:1].upper() + detalhe[1:],
            "concluido": all(passo in passos for passo in PASSOS_DA_CONFIGURACAO),
        },
        {
            "chave": "convidar_equipe",
            "rotulo": "Convidar a equipe",
            "detalhe": (
                _plural(convites, "convite enviado", "convites enviados")
                if convites
                else "Chame quem vai usar o sistema com você"
            ),
            "concluido": convites > 0 or "equipe" in passos,
        },
        {
            "chave": "primeira_locacao",
            "rotulo": "Fazer uma locação de teste",
            "detalhe": "Contrato, vistoria e assinatura com um cliente seu ou de teste",
            "concluido": primeira,
            **({} if primeira else {"acao": {"rotulo": "Começar", "destino": "nova_locacao"}}),
        },
    ]
    concluidos = sum(1 for item in itens if item["concluido"])
    return {
        "concluidos": concluidos,
        "total": len(itens),
        "pct": _pct(concluidos, len(itens)),
        "itens": itens,
    }


def _implantacao(usuario: Any, escopo: Escopo, empresa: Any) -> dict[str, Any]:
    contagem = _frota(escopo)
    convites = contas_selectors.convites_enviados()
    return {
        "teste": _teste(empresa),
        "primeiros_passos": _primeiros_passos(empresa, contagem["todos"], len(convites)),
        "convites": convites,
        "indicadores": {
            "frota_cadastrada": contagem["todos"],
            "alugados_agora": contagem["alugado"],
            "clientes": clientes_selectors.total_ativos(),
            "a_receber_centavos": financeiro_selectors.em_aberto(escopo.filiais),
        },
    }


# --- Variante `gerente` (tela Gerente) ---


def _aprovacoes_do_gerente(usuario: Any, escopo: Escopo) -> dict[str, Any]:
    pedidos = _aprovacoes_pendentes(usuario, escopo).order_by("criado_em", "id")
    total = pedidos.count()
    primeiros = list(pedidos[:ITENS_DE_APROVACAO])
    return {
        "total": total,
        "mais_antigo": _ha_quanto(primeiros[0].criado_em) if primeiros else None,
        "itens": [
            {
                "id": pedido.pk,
                "tipo": pedido.tipo,
                "titulo": pedido.titulo,
                "detalhe": pedido.detalhe,
                "acoes": ["recusar", "aprovar"],
            }
            for pedido in primeiros
        ],
    }


def _receita_da_semana(escopo: Escopo, fuso: ZoneInfo) -> dict[str, Any]:
    hoje = relogio.hoje()
    atual = _receita(escopo, 7, hoje, fuso)
    anterior = _receita(escopo, 7, hoje - timedelta(days=7), fuso)
    contexto = None
    if anterior and atual != anterior:
        variacao = int(
            (Decimal(abs(atual - anterior) * 100) / Decimal(anterior)).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
        )
        contexto = f"{variacao}% a {'mais' if atual > anterior else 'menos'} que a anterior"
    return _kpi(
        "receita_semana",
        "Receita da semana",
        "centavos",
        atual,
        contexto,
        tendencia=_tendencia(atual - anterior) if anterior else None,
    )


def _devolucoes_atrasadas(escopo: Escopo) -> dict[str, Any]:
    atrasadas = list(
        locacoes_selectors.das_filiais(escopo.filiais).filter(status="devolucao_atrasada")
    )
    antigas = sum(1 for x in atrasadas if locacoes_selectors.dias_de_atraso(x) > 2)
    return _kpi(
        "devolucoes_atrasadas",
        "Devoluções atrasadas",
        "numero",
        len(atrasadas),
        f"{antigas} há mais de 2 dias" if antigas else None,
    )


def _equipe_hoje(usuario: Any, escopo: Escopo, fuso: ZoneInfo) -> list[dict[str, Any]]:
    """USR-08: pessoas ativas ligadas às filiais do escopo, com o resumo do dia."""
    ids = filiais_selectors.usuarios_das_filiais(escopo.filiais) - {usuario.pk}
    locacoes_hoje = locacoes_selectors.criadas_hoje_por_vendedor(escopo.filiais)
    pessoas = contas_selectors.ativos_com_ultimo_uso(ids)
    vistorias_feitas: dict[int, int] = {}
    vistorias_do_dia = 0
    if any(p.perfil == "vistoriador" for p in pessoas):
        for filial in escopo.lista():
            vistorias_do_dia += len(vistorias_selectors.agenda(filial, "hoje")["resultados"])
            for pk, total in vistorias_selectors.concluidas_hoje_por_responsavel(filial).items():
                vistorias_feitas[pk] = vistorias_feitas.get(pk, 0) + total
    agora = relogio.agora()
    equipe = []
    for pessoa in pessoas:
        ultimo = pessoa.ultimo_uso  # type: ignore[attr-defined]
        if pessoa.perfil == "vistoriador" and vistorias_do_dia:
            feitas = vistorias_feitas.get(pessoa.pk, 0)
            do_dia = _plural(vistorias_do_dia, "vistoria feita", "vistorias feitas")
            resumo = f"{feitas} de {do_dia}"
        elif pessoa.perfil == "vendedor" and locacoes_hoje.get(pessoa.pk):
            resumo = f"{_plural(locacoes_hoje[pessoa.pk], 'locação', 'locações')} hoje"
        else:
            resumo = _ultimo_acesso(ultimo, fuso)
        equipe.append(
            {
                "usuario_id": pessoa.pk,
                "nome": pessoa.nome,
                "perfil": pessoa.perfil,
                "resumo": resumo,
                "online": ultimo is not None and agora - ultimo <= ONLINE,
            }
        )
    return equipe


def _gerente(usuario: Any, escopo: Escopo, periodo: str) -> dict[str, Any]:
    fuso = _fuso(escopo)
    contagem = _frota(escopo)
    meta = empresas_selectors.meta_ocupacao_pct()
    ocupacao = veiculos_selectors.ocupacao_da_frota(escopo.filiais, PERIODOS[periodo])
    livres, alugados, reservados = (
        contagem["disponivel"],
        contagem["alugado"],
        contagem["reservado"],
    )
    return {
        "aprovacoes": _aprovacoes_do_gerente(usuario, escopo),
        "kpis": [
            _kpi("ocupacao", "Ocupação", "pct", ocupacao, f"meta de {_pct_texto(meta)}"),
            _receita_da_semana(escopo, fuso),
            _devolucoes_atrasadas(escopo),
            _kpi("em_manutencao", "Em manutenção", None, None),  # app manutencao (fase 2)
        ],
        "equipe_hoje": _equipe_hoje(usuario, escopo, fuso),
        "frota_filial": {
            "total": contagem["todos"],
            "segmentos": [
                {"rotulo": "Livres", "quantidade": livres},
                {"rotulo": "Alugados", "quantidade": alugados},
                {"rotulo": "Reserv.", "quantidade": reservados},
                {
                    "rotulo": "Oficina e venda",
                    "quantidade": contagem["todos"] - livres - alugados - reservados,
                },
            ],
        },
    }


# --- Variante `vendedor` (fase 1: locação) ---


def _vendedor(usuario: Any, escopo: Escopo, periodo: str) -> dict[str, Any]:
    hoje = relogio.hoje()
    minhas = locacoes_selectors.das_filiais(escopo.filiais, vendedor_id=usuario.pk)
    ids = list(minhas.values_list("pk", flat=True))
    atraso = financeiro_selectors.atrasadas(escopo.filiais, hoje, origens=ids)
    parcelas = financeiro_selectors.atrasadas_das_origens(ids, hoje).filter(
        filial_id__in=escopo.filiais
    )
    return {
        "kpis": [
            _kpi(
                "minhas_locacoes_ativas",
                "Minhas locações ativas",
                "numero",
                locacoes_selectors.por_aba(minhas, "abertas").count(),
            ),
            _kpi(
                "devolvem_hoje",
                "Devolvem hoje",
                "numero",
                locacoes_selectors.por_aba(minhas, "devolvem_hoje").count(),
            ),
            _kpi(
                "parcelas_atrasadas",
                "Parcelas atrasadas",
                "numero",
                atraso.quantidade,
                (
                    f"{formatar_reais(atraso.centavos)} de "
                    f"{_plural(atraso.clientes, 'cliente', 'clientes')}"
                    if atraso.quantidade
                    else None
                ),
            ),
        ],
        "parcelas_atrasadas": [
            {
                "conta_id": conta.pk,
                "cliente": conta.cliente.nome,
                "locacao": conta.origem_codigo,
                "vencimento": conta.vencimento,
                "valor_centavos": conta.valor_centavos,
                "dias": (hoje - conta.vencimento).days,
                "acao": "cobrar",
            }
            for conta in parcelas
        ],
        "precisam_acao": [
            {
                "locacao_id": x.pk,
                "codigo": x.codigo,
                "cliente": x.cliente.nome,
                "situacao": {
                    chave: valor
                    for chave, valor in locacoes_selectors.situacao(
                        x, locacoes_selectors.sinais(x)
                    ).items()
                    if chave != "codigo"
                },
            }
            for x in locacoes_selectors.por_aba(minhas, "precisam_acao").order_by(
                "fim_previsto", "id"
            )
        ],
        "meta": None,  # vendas e comissões (fase 2)
        "funil": None,
        "comissao_prevista": None,
        "propostas": None,
    }


# --- Variante `vistoriador` ---


def _vistoriador(usuario: Any, escopo: Escopo, periodo: str) -> dict[str, Any]:
    filial = escopo.filial() or escopo.lista()[0]
    agenda = vistorias_selectors.agenda(filial, "hoje")
    return {"agenda": agenda, "avarias_abertas": agenda["avarias_abertas"]}


# --- Variante `financeiro` ---


def _para_hoje(escopo: Escopo) -> list[dict[str, Any]]:
    """USR-08: reembolsos a fazer e despesas a pagar vencendo até hoje (FIN-05)."""
    reembolsos = [
        {
            "texto": (
                f"Devolver {formatar_reais(r.valor_centavos)} a {r.cliente.nome} "
                f"{FORMA_DO_REEMBOLSO.get(r.forma, '')}"
            ).strip(),
            "tipo": "reembolso",
            "destino": {"chave": "reembolsos", "id": r.pk},
        }
        for r in financeiro_selectors.reembolsos_a_fazer(escopo.filiais)
    ]
    despesas = [
        {
            "texto": f"Pagar {d.descricao[:1].lower()}{d.descricao[1:]} · "
            f"{formatar_reais(d.valor_centavos)}",
            "tipo": "despesa",
            "destino": {"chave": "contas_a_pagar", "id": d.pk},
        }
        for d in financeiro_selectors.despesas_a_pagar_vencendo(escopo.filiais, relogio.hoje())
    ]
    return reembolsos + despesas


def _financeiro(usuario: Any, escopo: Escopo, periodo: str) -> dict[str, Any]:
    hoje = relogio.hoje()
    entra = financeiro_selectors.vencem_entre(escopo.filiais, hoje, hoje)
    atraso = financeiro_selectors.atrasadas(escopo.filiais, hoje)
    vencem_hoje = financeiro_selectors.despesas_a_pagar_vencendo(escopo.filiais, hoje).filter(
        vencimento=hoje
    )
    sai = financeiro_selectors.Soma(sum(d.valor_centavos for d in vencem_hoje), len(vencem_hoje))
    return {
        "kpis": [
            _kpi(
                "entra_hoje",
                "Entra hoje",
                "centavos",
                entra.centavos,
                _plural(entra.quantidade, "parcela", "parcelas"),
            ),
            _kpi(
                "sai_hoje",
                "Sai hoje",
                "centavos",
                sai.centavos,
                _plural(sai.quantidade, "conta a pagar", "contas a pagar"),
            ),
            _kpi(
                "em_atraso",
                "Em atraso",
                "centavos",
                atraso.centavos,
                _plural(atraso.clientes, "cliente", "clientes"),
            ),
            _kpi("saldo_em_contas", "Saldo em contas", None, None),  # fase 2
        ],
        "caixas_do_dia": financeiro_selectors.caixas_de_hoje(escopo.filiais, hoje),
        "para_hoje": _para_hoje(escopo),
        "fluxo_previsto": None,  # fase 2
        "conciliacao": None,
    }


# --- Entrada ---

VARIANTES: dict[str, Callable[[Any, Escopo, str], dict[str, Any]]] = {
    "geral": _geral,
    "gerente": _gerente,
    "vendedor": _vendedor,
    "vistoriador": _vistoriador,
    "financeiro": _financeiro,
}


def inicio(
    usuario: Any, variante: str, escopo: Escopo, periodo: str, empresa: Any
) -> dict[str, Any]:
    """O início da variante (a mesma de `eu.navegacao.inicio.variante`)."""
    if variante == "implantacao":
        blocos = _implantacao(usuario, escopo, empresa)
    else:
        blocos = VARIANTES[variante](usuario, escopo, periodo)
    return {
        "variante": variante,
        "saudacao": saudacao(getattr(usuario, "nome", ""), _fuso(escopo)),
        "atualizado_em": relogio.agora(),
        **blocos,
    }


# --- Configurações (`docs/api/configuracoes.md`) ---


def _modulo_do_cartao() -> dict[str, str]:
    """A tabela de item e app do menu (`contas.navegacao`), mais os cartões sem item."""
    do_menu = {
        chave: str(navegacao.ITENS[chave].modulo)
        for chave in ("marca", "filiais", "usuarios", "assinatura", "auditoria")
    }
    # O ramo é do app `empresas`, como a marca (T-259).
    return {**do_menu, "ramo": do_menu["marca"], **textos_de_configuracoes.MODULO_PROPRIO}


def configuracoes(usuario: Any, suporte: bool) -> dict[str, Any]:
    """`GET /api/configuracoes/`: os cartões da empresa inteira (ignora o `X-Filial`) e a faixa
    da implantação. Só os selectors listados em "Fontes" do contrato; cada um só é chamado
    quando o cartão dele vem."""
    modulos = navegacao.modulos_ativos()
    visiveis = textos_de_configuracoes.visiveis(_modulo_do_cartao(), modulos, suporte)
    empresa = plataforma_selectors.empresa_atual()
    assinatura = plataforma_selectors.assinatura(empresa)
    fontes = textos_de_configuracoes.Fontes(
        ramo=empresas_selectors.resumo_do_ramo() if "ramo" in visiveis else None,
        filiais=filiais_selectors.resumo_das_filiais_ativas() if "filiais" in visiveis else None,
        usuarios=(
            (
                assinatura["uso"]["usuarios"]["usado"],
                assinatura["uso"]["usuarios"]["limite"],
                contas_selectors.convites_pendentes(),
            )
            if "usuarios" in visiveis
            else None
        ),
        precos=(
            (
                veiculos_selectors.categorias_ativas(),
                locacoes_selectors.planos_especiais_ativos() if "locacoes" in modulos else None,
            )
            if "precos" in visiveis
            else None
        ),
        modelos=(
            contratos_selectors.resumo_dos_modelos() if "modelos_contrato" in visiveis else None
        ),
        assinatura={
            "plano": assinatura["plano"]["nome"],
            "status": assinatura["status"],
            "ciclo": assinatura["plano"]["ciclo"],
            "teste_fim": (assinatura["teste"] or {}).get("fim"),
            "pausada_ate": empresa.pausada_ate,
        },
    )
    passos = plataforma_selectors.implantacao(empresa)["passos"]
    return {
        "cartoes": textos_de_configuracoes.cartoes(visiveis, fontes),
        "implantacao": textos_de_configuracoes.implantacao(passos),
    }
