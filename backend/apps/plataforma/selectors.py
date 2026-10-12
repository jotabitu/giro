"""Leituras da plataforma: situação da empresa, uso do plano e assinatura (PLT-01, PLT-03, IMP-05).

A `situacao` sai de uma anotação SQL só (`com_situacao`), usada pela lista (filtro e
contagens) e pelo detalhe: a ordem da tabela do contrato fica num lugar.
"""

from datetime import date, timedelta
from typing import Any

from django.db.models import Case, CharField, Count, F, Q, QuerySet, Value, When
from django_tenants.utils import get_public_schema_name

from comum import relogio
from comum.conexao import conexao

from .models import Empresa, Item, UsoEmpresa
from .services import PASSOS_IMPLANTACAO, chegou_a_90, endereco_de_acesso, etapa_do_funil

DIAS_PARA_IMPLANTACAO_PARADA = 3  # IMP-05
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

TOM = {
    "cancelando": "alerta",
    "suspensa": "perigo",
    "fatura_atrasada": "perigo",
    "implantacao_parada": "alerta",
    "perto_do_limite": "alerta",
    "em_teste": "info",
    "pausada": "neutro",
    "ativa": "sucesso",
    "cancelada": "neutro",
}
ABA = {
    "cancelando": "saindo",
    "suspensa": "com_problema",
    "fatura_atrasada": "com_problema",
    "implantacao_parada": "com_problema",
    "perto_do_limite": "com_problema",
}
SITUACOES_FILTRAVEIS = ("em_teste", "com_problema", "saindo", "ativa")

FAIXA_AVISO = {
    "inadimplente": "Há uma fatura da assinatura em atraso. Pague para evitar a suspensão.",
    "suspensa": (
        "Sua empresa está suspensa. Você pode ver e exportar os dados, mas não criar locações, "
        "vendas nem cobranças. Ao pagar, o acesso volta na hora."
    ),
    "pausada": (
        "Sua empresa está pausada. Você pode ver os dados. "
        "Para voltar a operar, retome a assinatura."
    ),
}
STATUS_SOMENTE_LEITURA = frozenset({"suspensa", "pausada", "cancelada"})


def empresa_atual() -> Empresa:
    """A `Empresa` do schema corrente (contrato da plataforma, interface interna)."""
    empresa = getattr(conexao(), "tenant", None)
    if not isinstance(empresa, Empresa) or empresa.schema_name == get_public_schema_name():
        raise RuntimeError("Sem empresa na conexão.")
    return empresa


def _dia_mes(dia: date | None) -> str:
    return f"{dia.day:02d} {MESES[dia.month - 1]}" if dia else ""


# --- Situação ---


def _perto_do_limite() -> Q:
    condicao = Q()
    for item in Item.values:
        condicao |= Q(**{f"_folga_90_{item}__lte": 0})
    return condicao


def com_situacao(queryset: QuerySet[Empresa] | None = None) -> QuerySet[Empresa]:
    """Anota `situacao_codigo` e `aba` na ordem da tabela do contrato (a primeira que vale)."""
    hoje = relogio.hoje()
    parada_desde = relogio.agora() - timedelta(days=DIAS_PARA_IMPLANTACAO_PARADA)
    qs = queryset if queryset is not None else Empresa.objects.all()
    # 9 × limite − 10 × uso ≤ 0  ⇔  uso ≥ 90% do limite. Limite nulo dá nulo, que não passa.
    folgas = {
        f"_folga_90_{item}": F(f"plano__limite_{item}") * 9 - F(f"uso__{item}") * 10
        for item in Item.values
    }
    codigo = Case(
        When(status="cancelada", acesso_ate__gte=hoje, then=Value("cancelando")),
        When(status="suspensa", then=Value("suspensa")),
        When(status="inadimplente", then=Value("fatura_atrasada")),
        When(
            Q(status="em_teste", etapa_implantacao_desde__lte=parada_desde)
            & ~Q(etapa_implantacao="concluida"),
            then=Value("implantacao_parada"),
        ),
        When(_perto_do_limite(), then=Value("perto_do_limite")),
        When(status="em_teste", then=Value("em_teste")),
        When(status="pausada", then=Value("pausada")),
        When(status="ativa", then=Value("ativa")),
        default=Value("cancelada"),
        output_field=CharField(),
    )
    aba = Case(
        *[When(situacao_codigo=c, then=Value(a)) for c, a in ABA.items()],
        default=Value(""),
        output_field=CharField(),
    )
    return (
        qs.exclude(schema_name=get_public_schema_name())
        .select_related("plano", "uso")
        .annotate(**folgas)
        .annotate(situacao_codigo=codigo)
        .annotate(aba=aba)
    )


def _primeiro_passo_aberto(passos: dict[str, Any]) -> int:
    for numero, (passo, _rotulo) in enumerate(PASSOS_IMPLANTACAO, start=1):
        if passo not in passos:
            return numero
    return len(PASSOS_IMPLANTACAO)


def _uso(empresa: Empresa) -> UsoEmpresa:
    try:
        return empresa.uso
    except UsoEmpresa.DoesNotExist:
        return UsoEmpresa(empresa=empresa)


def situacao(empresa: Empresa) -> dict[str, str]:
    """`{codigo, rotulo, tom}`. A empresa precisa vir de `com_situacao`."""
    codigo: str = empresa.situacao_codigo
    if codigo == "cancelando":
        rotulo = f"Cancela em {_dia_mes(empresa.acesso_ate)}"
    elif codigo == "suspensa":
        rotulo = "Suspensa"
    elif codigo == "fatura_atrasada":
        # Os dias de atraso vêm da fatura (cobrança, fase 2).
        rotulo = "Fatura atrasada"
    elif codigo == "implantacao_parada":
        passo = _primeiro_passo_aberto(_uso(empresa).passos_implantacao)
        rotulo = f"Parada no passo {passo}"
    elif codigo == "perto_do_limite":
        rotulo = "Perto do limite"
    elif codigo == "em_teste":
        dia = (relogio.hoje() - empresa.teste_inicio).days + 1 if empresa.teste_inicio else 1
        rotulo = f"Teste · dia {dia}"
    elif codigo == "pausada":
        rotulo = (
            f"Pausada até {_dia_mes(empresa.pausada_ate)}" if empresa.pausada_ate else "Pausada"
        )
    elif codigo == "ativa":
        rotulo = "Ativa"
    else:
        rotulo = "Cancelada"
    return {"codigo": codigo, "rotulo": rotulo, "tom": TOM[codigo]}


# --- Lista ---


def filtrar_empresas(
    *,
    situacao_aba: str | None = None,
    plano: str | None = None,
    status: str | None = None,
    busca: str | None = None,
) -> QuerySet[Empresa]:
    qs = com_situacao()
    if situacao_aba in ("em_teste", "ativa"):
        qs = qs.filter(status=situacao_aba)
    elif situacao_aba in ("com_problema", "saindo"):
        qs = qs.filter(aba=situacao_aba)  # type: ignore[misc]
    if plano:
        qs = qs.filter(plano_id=plano)
    if status:
        qs = qs.filter(status=status)
    if busca and busca.strip():
        termo = busca.strip()
        condicao = Q(nome_exibicao__icontains=termo) | Q(subdominio__icontains=termo.lower())
        digitos = "".join(c for c in termo if c.isdigit())
        if len(digitos) >= 3:
            condicao |= Q(cnpj__contains=digitos)
        qs = qs.filter(condicao)
    return qs


def contagens_das_empresas() -> dict[str, int]:
    """Abas da lista. `em_teste` e `ativa` contam o status; as outras, a situação."""
    total: dict[str, int] = com_situacao().aggregate(
        todas=Count("id"),
        pagantes=Count("id", filter=~Q(status="em_teste")),
        em_teste=Count("id", filter=Q(status="em_teste")),
        ativa=Count("id", filter=Q(status="ativa")),
        com_problema=Count("id", filter=Q(aba="com_problema")),
        saindo=Count("id", filter=Q(aba="saindo")),
    )
    return total


# --- Uso e assinatura ---


def uso_do_plano(empresa: Empresa | None = None) -> dict[str, dict[str, Any]]:
    """O dicionário `uso` de `GET /api/assinatura/` (PLT-03)."""
    empresa = empresa or empresa_atual()
    uso = UsoEmpresa.objects.filter(empresa_id=empresa.pk).first() or UsoEmpresa()
    plano = empresa.plano
    resultado: dict[str, dict[str, Any]] = {}
    for item in Item.values:
        usado = int(getattr(uso, item))
        limite = plano.limite(item) if plano else None
        resultado[item] = {
            "usado": usado,
            "limite": limite,
            "aviso": chegou_a_90(usado, limite),
            "bloqueado": limite is not None and usado >= limite,
        }
    return resultado


def dias_restantes(empresa: Empresa) -> int | None:
    if empresa.teste_fim is None:
        return None
    return max(0, (empresa.teste_fim - relogio.hoje()).days)


def assinatura(empresa: Empresa | None = None) -> dict[str, Any]:
    empresa = empresa or empresa_atual()
    empresa = Empresa.objects.select_related("plano").get(pk=empresa.pk)
    plano = empresa.plano
    return {
        "plano": {
            "nome": plano.nome if plano else "",
            "preco_contratado_centavos": empresa.preco_contratado_centavos,
            "ciclo": empresa.ciclo,
        },
        "status": empresa.status,
        "teste": (
            {"fim": empresa.teste_fim, "dias_restantes": dias_restantes(empresa)}
            if empresa.status == Empresa.Status.EM_TESTE
            else None
        ),
        "faixa_aviso": FAIXA_AVISO.get(empresa.status),
        "uso": uso_do_plano(empresa),
        "somente_leitura": empresa.status in STATUS_SOMENTE_LEITURA,
    }


# --- Detalhe (Plat-Empresa-Detalhe) ---


def implantacao(empresa: Empresa) -> dict[str, Any]:
    passos = _uso(empresa).passos_implantacao
    return {
        "etapa_funil": etapa_do_funil(passos),
        "concluidos": sum(1 for passo, _ in PASSOS_IMPLANTACAO if passo in passos),
        "total": len(PASSOS_IMPLANTACAO),
        "passos": [
            {"passo": passo, "rotulo": rotulo, "concluido_em": passos.get(passo)}
            for passo, rotulo in PASSOS_IMPLANTACAO
        ],
    }


def detalhe_empresa(empresa: Empresa) -> dict[str, Any]:
    uso = uso_do_plano(empresa)
    return {
        "id": empresa.pk,
        "razao_social": empresa.razao_social,
        "nome_exibicao": empresa.nome_exibicao,
        "cnpj": empresa.cnpj,
        "subdominio": empresa.subdominio,
        "endereco_acesso": endereco_de_acesso(empresa.subdominio or ""),
        "cidade": empresa.cidade,
        "uf": empresa.uf,
        "responsavel": {
            "nome": empresa.responsavel_nome,
            "email": empresa.responsavel_email,
            "telefone": empresa.responsavel_telefone,
        },
        "cliente_desde": empresa.criado_em.date() if empresa.criado_em else None,
        "plano": {"id": empresa.plano.pk, "nome": empresa.plano.nome} if empresa.plano else None,
        "ciclo": empresa.ciclo,
        "preco_contratado_centavos": empresa.preco_contratado_centavos,
        "status": empresa.status,
        "situacao": situacao(empresa),
        "teste": {
            "inicio": empresa.teste_inicio,
            "fim": empresa.teste_fim,
            "dias_restantes": dias_restantes(empresa),
        },
        "uso": {
            item: {k: v for k, v in valores.items() if k != "bloqueado"}
            for item, valores in uso.items()
        },
        "implantacao": implantacao(empresa),
        "locacoes_total": _uso(empresa).locacoes_total,
        # Chamados, faturas e ações sobre a empresa são da fase 2.
        "chamados_abertos": 0,
        "suporte_bloqueado": empresa.suporte_bloqueado,
        "faturas_recentes": [],
        "acoes": {
            "entrar_como_suporte": False,
            "estender_teste": False,
            "mudar_plano": False,
            "suspender": False,
        },
    }


def item_da_lista(empresa: Empresa) -> dict[str, Any]:
    uso = _uso(empresa)
    return {
        "id": empresa.pk,
        "nome_exibicao": empresa.nome_exibicao,
        "subdominio": empresa.subdominio,
        "cidade": empresa.cidade,
        "uf": empresa.uf,
        "plano": {"id": empresa.plano.pk, "nome": empresa.plano.nome} if empresa.plano else None,
        "status": empresa.status,
        "uso": {
            "veiculos": uso.veiculos,
            "limite_veiculos": empresa.plano.limite_veiculos if empresa.plano else None,
            "filiais": uso.filiais,
            "usuarios": uso.usuarios,
        },
        "situacao": situacao(empresa),
        "ultimo_acesso_em": uso.ultimo_acesso_em,
    }


def passos_implantacao(empresa: Empresa) -> dict[str, Any]:
    """`{passo: concluído em}` da implantação (IMP-05), lido do `public` (painel da empresa)."""
    return dict(_uso(empresa).passos_implantacao or {})
