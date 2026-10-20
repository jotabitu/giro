"""Leituras da plataforma: situação da empresa, uso do plano e assinatura (PLT-01, PLT-03, IMP-05).

A `situacao` sai de uma anotação SQL só (`com_situacao`), usada pela lista (filtro e
contagens) e pelo detalhe: a ordem da tabela do contrato fica num lugar.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from django.db.models import Case, CharField, Count, F, Q, QuerySet, Value, When
from django.utils import timezone
from django_tenants.utils import get_public_schema_name

from comum import empresa as comum_empresa
from comum import relogio
from comum.conexao import conexao
from comum.dinheiro import formatar_reais

from . import catalogo
from .calendario import MESES_DE_PAUSA, dia_e_mes, dia_mes_e_ano, periodo_da_pausa
from .models import (
    TENTATIVAS_DO_CARTAO,
    Empresa,
    FaturaAssinatura,
    FormaAssinatura,
    FormaPagamentoAssinatura,
    Item,
    MotivoCancelamento,
    Plano,
    Recurso,
    SituacaoNota,
    StatusFatura,
    StatusFormaPagamento,
    TipoFatura,
    UsoEmpresa,
)
from .services import (
    PASSOS_IMPLANTACAO,
    STATUS_QUE_CANCELAM,
    STATUS_QUE_MUDAM_DE_PLANO,
    ProximaMensalidade,
    cancelamento_marcado,
    chegou_a_90,
    datas_de_cancelar,
    dia_do_acesso,
    endereco_de_acesso,
    etapa_do_funil,
    excede_no_plano,
    fim_do_periodo_pago,
    pausa_marcada,
    plano_acima,
    proxima_mensalidade,
)

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
}
# Provisório até a tela existir (T-214 ou T-200): o frontend mostra o que vier.
FAIXA_DA_PAUSADA = "Assinatura pausada até {}. Você só consulta os dados."
STATUS_SOMENTE_LEITURA = frozenset({"suspensa", "pausada", "cancelada"})
# Forma de pagamento, pagar e dados fiscais: a `suspensa` também, para voltar a `ativa` (PLT-13).
STATUS_QUE_PAGAM = frozenset({"em_teste", "ativa", "inadimplente", "suspensa"})
PERFIL_ADMINISTRADOR = "administrador"


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
    parada_desde = relogio.agora() - timedelta(days=DIAS_PARA_IMPLANTACAO_PARADA)
    qs = queryset if queryset is not None else Empresa.objects.all()
    # 9 × limite − 10 × uso ≤ 0  ⇔  uso ≥ 90% do limite. Limite nulo dá nulo, que não passa.
    folgas = {
        f"_folga_90_{item}": F(f"plano__limite_{item}") * 9 - F(f"uso__{item}") * 10
        for item in Item.values
    }
    codigo = Case(
        # Cancelamento marcado (`cancelamento.md`): acesso até `acesso_ate`, ainda não cancelada.
        When(Q(acesso_ate__isnull=False) & ~Q(status="cancelada"), then=Value("cancelando")),
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


def _rotulo_da_fatura_atrasada(empresa: Empresa) -> str:
    """ "Fatura 12 dias atrasada", pela fatura atrasada mais antiga (T-184)."""
    vencimento = (
        FaturaAssinatura.objects.filter(empresa=empresa, status=StatusFatura.ATRASADA)
        .order_by("vencimento")
        .values_list("vencimento", flat=True)
        .first()
    )
    if vencimento is None:
        return "Fatura atrasada"
    dias = (relogio.hoje() - vencimento).days
    return f"Fatura {dias} {'dia' if dias == 1 else 'dias'} atrasada"


def faturas_recentes(empresa: Empresa) -> list[dict[str, Any]]:
    """As 5 faturas mais novas da empresa, da mais nova para a mais antiga (painel da
    plataforma). A 1ª de quem passou pelo teste leva "1ª cobrança após o teste"."""
    faturas = FaturaAssinatura.objects.filter(empresa=empresa).order_by("-vencimento", "-numero")
    return [
        {
            "codigo": fatura.codigo,
            "vencimento": fatura.vencimento,
            "valor_centavos": fatura.valor_centavos,
            "status": fatura.status,
            "observacao": (
                "1ª cobrança após o teste"
                if fatura.numero == 1 and empresa.teste_fim is not None
                else None
            ),
        }
        for fatura in faturas[:5]
    ]


def situacao(empresa: Empresa) -> dict[str, str]:
    """`{codigo, rotulo, tom}`. A empresa precisa vir de `com_situacao`."""
    codigo: str = empresa.situacao_codigo
    if codigo == "cancelando":
        # O dia em que vira `cancelada`: o seguinte a `acesso_ate` (plataforma.md).
        cancela = empresa.acesso_ate + timedelta(days=1) if empresa.acesso_ate else None
        rotulo = f"Cancela em {_dia_mes(cancela)}"
    elif codigo == "suspensa":
        rotulo = "Suspensa"
    elif codigo == "fatura_atrasada":
        rotulo = _rotulo_da_fatura_atrasada(empresa)
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
        rotulo = "Dados apagados" if empresa.apagada_em else "Cancelada"  # AUD-08
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


def assinatura(empresa: Empresa | None = None, usuario: Any = None) -> dict[str, Any]:
    """`GET /api/assinatura/` (PLT-01, PLT-03, PLT-11, PLT-13, PLT-15; assinatura.md). Os blocos
    `forma_pagamento`, `dados_fiscais`, `oferta` e `acoes` só para o administrador (e para o
    suporte, que lê com as ações desligadas)."""
    empresa = empresa or empresa_atual()
    empresa = Empresa.objects.select_related("plano", "plano_proximo").get(pk=empresa.pk)
    plano = empresa.plano
    proxima = proxima_mensalidade(empresa)
    dados: dict[str, Any] = {
        "plano": {
            "id": plano.pk if plano else None,
            "nome": plano.nome if plano else "",
            "preco_contratado_centavos": empresa.preco_contratado_centavos,
            "ciclo": empresa.ciclo,
        },
        "status": empresa.status,
        "teste": (
            {
                "inicio": empresa.teste_inicio,
                "fim": empresa.teste_fim,
                "dias_restantes": dias_restantes(empresa),
            }
            if empresa.status == Empresa.Status.EM_TESTE
            else None
        ),
        "proxima_fatura": _proxima_fatura(empresa, proxima),
        "plano_proximo": _plano_proximo(empresa, proxima),
        "faixa_aviso": _faixa_aviso(empresa),
        "uso": uso_do_plano(empresa),
        "somente_leitura": empresa.status in STATUS_SOMENTE_LEITURA,
        "cancelamento": _cancelamento(empresa),
        "pausa": _pausa(empresa),
    }
    if getattr(usuario, "perfil", None) != PERFIL_ADMINISTRADOR:
        return dados
    return {
        **dados,
        "forma_pagamento": forma_de_pagamento(empresa),
        "dados_fiscais": dados_fiscais(empresa),
        "oferta": oferta(empresa),
        "acoes": acoes_da_assinatura(empresa, usuario),
    }


def _faixa_aviso(empresa: Empresa) -> str | None:
    """A faixa no topo (`plataforma.md`). O cancelamento marcado não tem faixa: o aviso fica na
    `Admin-Assinatura` (`cancelamento.md`)."""
    if empresa.status == Empresa.Status.PAUSADA and empresa.pausada_ate:
        return FAIXA_DA_PAUSADA.format(dia_e_mes(empresa.pausada_ate))
    return FAIXA_AVISO.get(empresa.status)


def _cancelamento(empresa: Empresa) -> dict[str, Any] | None:
    """Só com cancelamento marcado (PLT-06): o texto pronto do estado da `Admin-Assinatura`."""
    if not cancelamento_marcado(empresa) or empresa.acesso_ate is None:
        return None
    acesso = dia_do_acesso(empresa, empresa.acesso_ate)
    return {
        "pedido_em": empresa.cancelamento_pedido_em,
        "motivo": empresa.motivo_cancelamento or None,
        "acesso_ate": empresa.acesso_ate,
        "rotulo": f"Assinatura cancelada. Você tem acesso até {acesso}.",
    }


def _pausa(empresa: Empresa) -> dict[str, Any] | None:
    """Só com pausa marcada (PLT-06): agendada enquanto `ativa`, em andamento na `pausada`.
    Textos provisórios até a tela existir (T-214 ou T-200)."""
    inicio, ate = empresa.pausa_inicio, empresa.pausada_ate
    if inicio is None or ate is None:
        return None
    volta = ate + timedelta(days=1)
    meses = (volta.year * 12 + volta.month) - (inicio.year * 12 + inicio.month)
    if empresa.status == Empresa.Status.PAUSADA:
        situacao = "em_andamento"
        rotulo = f"Assinatura pausada até {dia_e_mes(ate)}. Volta sozinha em {dia_e_mes(volta)}."
    else:
        situacao = "agendada"
        rotulo = f"Pausa marcada de {dia_e_mes(inicio)} a {dia_e_mes(ate)}. Até lá, tudo continua."
    return {
        "situacao": situacao,
        "meses": meses,
        "inicio": inicio,
        "ate": ate,
        "volta_em": volta,
        "rotulo": rotulo,
    }


def _proxima_fatura(empresa: Empresa, proxima: ProximaMensalidade | None) -> dict[str, Any] | None:
    """O "R$ 449,00 por mês, a partir de 22 out" (PLT-01). Nula na `pausada` e na `cancelada`,
    e com o cancelamento ou a pausa marcados: nada vai ser cobrado (`cancelamento.md`)."""
    sem_proxima = empresa.status in (Empresa.Status.PAUSADA, Empresa.Status.CANCELADA)
    if proxima is None or sem_proxima or cancelamento_marcado(empresa) or pausa_marcada(empresa):
        return None
    return {
        "vencimento": proxima.vencimento,
        "valor_centavos": proxima.valor_centavos,
        "descricao": proxima.descricao,
    }


def _plano_proximo(empresa: Empresa, proxima: ProximaMensalidade | None) -> dict[str, Any] | None:
    """O downgrade (PLT-04) ou a mudança de ciclo da equipe agendados."""
    if empresa.plano_proximo is None:
        return None
    return {
        "id": empresa.plano_proximo.pk,
        "nome": empresa.plano_proximo.nome,
        "ciclo": empresa.ciclo_proximo or empresa.ciclo,
        "vale_em": proxima.vencimento if proxima else None,
    }


def _situacao_do_cartao(empresa: Empresa, forma: FormaPagamentoAssinatura) -> dict[str, str]:
    recusada = (
        FaturaAssinatura.objects.filter(
            empresa_id=empresa.pk,
            status__in=[StatusFatura.ABERTA, StatusFatura.ATRASADA],
            cartao_recusado_em__isnull=False,
        )
        .order_by("-cartao_recusado_em")
        .first()
    )
    if recusada is not None:
        rotulo = (
            "O cartão foi recusado de novo. Pague a fatura por Pix ou boleto."
            if recusada.tentativas_cartao >= TENTATIVAS_DO_CARTAO
            else "O cartão foi recusado. Tentamos de novo amanhã."
        )
        return {"codigo": "cartao_recusado", "rotulo": rotulo, "tom": "perigo"}
    if not forma.cartao_final:
        return {
            "codigo": "cartao_na_primeira_fatura",
            "rotulo": "Você cadastra o cartão ao pagar a primeira fatura.",
            "tom": "info",
        }
    periodo = "todo ano" if empresa.ciclo == Empresa.Ciclo.ANUAL else "todo mês"
    bandeira = forma.cartao_bandeira.capitalize() or "Cartão"
    return {
        "codigo": "ativa",
        "rotulo": f"Cartão {bandeira} final {forma.cartao_final} · cobrança automática {periodo}",
        "tom": "sucesso",
    }


def _situacao_da_forma(empresa: Empresa, forma: FormaPagamentoAssinatura | None) -> dict[str, str]:
    """A primeira que valer, na ordem do contrato (PLT-02, PLT-13)."""
    if forma is None or not forma.forma:
        rotulo = "Nenhuma cadastrada."
        if empresa.status == Empresa.Status.EM_TESTE and empresa.teste_fim:
            rotulo += f" Escolha até {dia_e_mes(empresa.teste_fim)} para não perder o acesso."
        return {"codigo": "sem_forma", "rotulo": rotulo, "tom": "alerta"}
    if forma.forma == FormaAssinatura.CARTAO:
        return _situacao_do_cartao(empresa, forma)
    if forma.forma == FormaAssinatura.PIX_AUTOMATICO:
        if forma.status == StatusFormaPagamento.PENDENTE:
            return {
                "codigo": "aguardando_autorizacao",
                "rotulo": "Autorize o Pix automático no app do seu banco.",
                "tom": "alerta",
            }
        return {"codigo": "ativa", "rotulo": "Pix automático autorizado", "tom": "sucesso"}
    return {"codigo": "ativa", "rotulo": "Boleto enviado por e-mail 5 dias antes", "tom": "sucesso"}


def forma_de_pagamento(empresa: Empresa) -> dict[str, Any]:
    """PLT-13. O token do cartão nunca sai daqui: só a bandeira e o final (ADR 0023)."""
    forma = FormaPagamentoAssinatura.objects.filter(empresa_id=empresa.pk).first()
    codigo = (forma.forma if forma else "") or None
    return {
        "forma": codigo,
        "situacao": _situacao_da_forma(empresa, forma),
        "cartao": (
            {"bandeira": forma.cartao_bandeira, "final": forma.cartao_final}
            if forma and forma.cartao_final
            else None
        ),
        # Último dia para escolher sem ir a `suspensa` no dia seguinte (PLT-01, PLT-13).
        "prazo": (
            empresa.teste_fim
            if empresa.status == Empresa.Status.EM_TESTE and codigo is None
            else None
        ),
    }


def dados_fiscais(empresa: Empresa) -> dict[str, Any]:
    """PLT-15: CNPJ só com dígitos; `endereco` nulo antes da matriz (passo 6)."""
    return {
        "razao_social": empresa.razao_social,
        "cnpj": empresa.cnpj,
        "endereco": empresa.endereco,
        "email_cobranca": empresa.email_cobranca,
    }


def oferta(empresa: Empresa) -> dict[str, Any] | None:
    """O cartão do plano acima (PLT-11): o primeiro plano ativo acima do atual pela `ordem`, com
    o que ele inclui e o atual não. Nulo no Completo."""
    plano = empresa.plano
    if plano is None:
        return None
    ativos = Plano.objects.filter(ativo=True).order_by("ordem", "id")
    acima = next((p for p in ativos if plano_acima(p, plano)), None)
    if acima is None:
        return None
    return {
        "titulo": catalogo.TITULO_DA_OFERTA,
        "plano": {
            "id": acima.pk,
            "nome": acima.nome,
            "preco_mensal_centavos": acima.preco_mensal_centavos,
        },
        "itens": list(catalogo.textos(acima.nome).a_mais),
    }


def acoes_da_assinatura(empresa: Empresa, usuario: Any) -> dict[str, bool]:
    """Perfil, estado da empresa e as tabelas do início de assinatura.md e de cancelamento.md. O
    suporte lê, nunca escreve (PLT-07, CA-ASS-19): tudo `false` para ele."""
    escreve = getattr(usuario, "perfil", None) == PERFIL_ADMINISTRADOR and not getattr(
        usuario, "e_suporte", False
    )
    marcado = cancelamento_marcado(empresa)
    muda = escreve and empresa.status in STATUS_QUE_MUDAM_DE_PLANO and not marcado
    paga = escreve and empresa.status in STATUS_QUE_PAGAM
    hoje = relogio.hoje()
    ativa = empresa.status == Empresa.Status.ATIVA
    inicio = empresa.pausa_inicio
    return {
        "mudar_plano": muda,
        "desfazer_mudanca_plano": (
            muda and empresa.plano_proximo_id is not None and not empresa.ciclo_proximo
        ),
        "escolher_forma_pagamento": paga,
        "editar_dados_fiscais": paga,
        "cancelar": escreve and not marcado and empresa.status in STATUS_QUE_CANCELAM,
        "desfazer_cancelamento": (
            escreve and marcado and empresa.acesso_ate is not None and hoje <= empresa.acesso_ate
        ),
        "pausar": escreve and ativa and not marcado and inicio is None,
        "voltar_pausa": escreve and empresa.status == Empresa.Status.PAUSADA,
        "desistir_pausa": escreve and ativa and inicio is not None and hoje < inicio,
    }


# --- Admin-Cancelar (PLT-06, AUD-08; cancelamento.md) ---

TEXTO_DO_EXPORTAR = (
    "Exportar baixa a auditoria em CSV. O resto dos seus dados você pede à equipe Giro."
)
PLANO_DA_ALTERNATIVA = "Essencial"
ESTADOS_QUE_TERMINAM_COM_DIVIDA = frozenset({Empresa.Status.INADIMPLENTE, Empresa.Status.SUSPENSA})


def _plano_resumo(empresa: Empresa, fim_pago: date | None) -> str:
    """ "Plano Profissional · em teste até 21 out", "· mensal" ou "· anual até 21 out 2027"."""
    nome = f"Plano {empresa.plano.nome}" if empresa.plano else "Plano"
    if empresa.status == Empresa.Status.EM_TESTE and empresa.teste_fim:
        return f"{nome} · em teste até {dia_e_mes(empresa.teste_fim)}"
    if empresa.ciclo == Empresa.Ciclo.ANUAL:
        return f"{nome} · anual até {dia_mes_e_ano(fim_pago)}" if fim_pago else f"{nome} · anual"
    return f"{nome} · mensal"


def _resumo_dos_limites(plano: Plano) -> str:
    """ "Até 30 veículos, 1 filial e 3 usuários." (só os itens com limite)."""
    partes = []
    for item, singular in (("veiculos", "veículo"), ("filiais", "filial"), ("usuarios", "usuário")):
        limite = plano.limite(item)
        if limite is not None:
            partes.append(f"{limite} {singular if limite == 1 else Item(item).label}")
    if not partes:
        return "Sem limite de veículos, filiais e usuários."
    texto = partes[0] if len(partes) == 1 else f"{', '.join(partes[:-1])} e {partes[-1]}"
    return f"Até {texto}."


def _alternativa_essencial(empresa: Empresa) -> dict[str, Any] | None:
    """Só quando a empresa pode mudar de plano (`em_teste` ou `ativa`, PLT-04) e não está no
    Essencial. `cabe` e `excede` são os da linha do Essencial em `GET planos/`."""
    if empresa.status not in STATUS_QUE_MUDAM_DE_PLANO or cancelamento_marcado(empresa):
        return None
    essencial = Plano.objects.filter(nome=PLANO_DA_ALTERNATIVA, ativo=True).first()
    if essencial is None or essencial.pk == empresa.plano_id:
        return None
    uso = UsoEmpresa.objects.filter(empresa_id=empresa.pk).first() or UsoEmpresa()
    excede = excede_no_plano(empresa, essencial, uso)
    return {
        "plano": {
            "id": essencial.pk,
            "nome": essencial.nome,
            "preco_mensal_centavos": essencial.preco_mensal_centavos,
        },
        "resumo": _resumo_dos_limites(essencial),
        "cabe": not excede,
        "excede": excede,
    }


def _alternativa_pausar(empresa: Empresa, fim_pago: date | None) -> dict[str, Any] | None:
    """Só quando `acoes.pausar` seria `true` (CA-ASS-37): `ativa`, sem cancelamento nem pausa."""
    pode = (
        empresa.status == Empresa.Status.ATIVA
        and not cancelamento_marcado(empresa)
        and not pausa_marcada(empresa)
    )
    if not pode or fim_pago is None:
        return None
    inicio = periodo_da_pausa(fim_pago + timedelta(days=1), MESES_DE_PAUSA[0]).inicio
    return {
        "meses": list(MESES_DE_PAUSA),
        "inicio": inicio,
        "texto": f"A pausa começa em {dia_e_mes(inicio)}, no fim do período pago.",
    }


def _cobrancas_futuras(empresa: Empresa, anual_pago: bool) -> str:
    """A linha "Cobranças futuras" pelo estado (`cancelamento.md`, tabela do `o_que_acontece`)."""
    if empresa.status in ESTADOS_QUE_TERMINAM_COM_DIVIDA:
        return "nenhuma nova. A fatura em atraso continua devida."
    if empresa.status == Empresa.Status.PAUSADA:
        return "nenhuma"
    diferencas = list(
        FaturaAssinatura.objects.filter(
            empresa_id=empresa.pk,
            tipo=TipoFatura.DIFERENCA_PLANO,
            status__in=[StatusFatura.ABERTA, StatusFatura.ATRASADA],
        ).order_by("vencimento", "numero")
    )
    if len(diferencas) == 1:
        fatura = diferencas[0]
        valor = formatar_reais(int(fatura.valor_centavos))
        return f"nenhuma nova. A fatura {fatura.codigo}, de {valor}, continua devida."
    if diferencas:
        codigos = [f.codigo for f in diferencas]
        lista = f"{', '.join(codigos[:-1])} e {codigos[-1]}"
        return f"nenhuma nova. As faturas {lista} continuam devidas."
    if anual_pago:
        return "nenhuma. Os meses que faltam não são devolvidos."
    return "nenhuma"


def tela_do_cancelamento(empresa: Empresa) -> dict[str, Any]:
    """`GET /api/assinatura/cancelamento/`: o que a `Admin-Cancelar` mostra, montado para hoje
    pela mesma conta do `POST` (`datas_de_cancelar`). Não grava nada. O cancelamento marcado é
    recusado antes, na view (409)."""
    empresa = Empresa.objects.select_related("plano").get(pk=empresa.pk)
    hoje = relogio.hoje()
    fim_pago = fim_do_periodo_pago(empresa)
    datas = datas_de_cancelar(empresa, hoje)
    anual_pago = (
        empresa.ciclo == Empresa.Ciclo.ANUAL
        and datas.acesso_ate is not None
        and datas.acesso_ate == fim_pago
    )
    if datas.acesso_ate is None:
        acesso = "termina agora"
    elif anual_pago:
        acesso = f"continua até {dia_mes_e_ano(datas.acesso_ate)}, sem devolução"
    else:
        acesso = f"continua até {dia_e_mes(datas.acesso_ate)}"
    return {
        "empresa": empresa.nome_exibicao,
        "plano_resumo": _plano_resumo(empresa, fim_pago),
        "motivos": [
            {"codigo": codigo, "rotulo": rotulo} for codigo, rotulo in MotivoCancelamento.choices
        ],
        "alternativas": {
            "pausar": _alternativa_pausar(empresa, fim_pago),
            "mudar_para_essencial": _alternativa_essencial(empresa),
        },
        "o_que_acontece": [
            {"codigo": "acesso", "rotulo": "Acesso", "valor": acesso},
            {
                "codigo": "cobrancas",
                "rotulo": "Cobranças futuras",
                "valor": _cobrancas_futuras(empresa, anual_pago),
            },
            {"codigo": "dados", "rotulo": "Seus dados", "valor": "guardados por 90 dias"},
            {"codigo": "apagamento", "rotulo": "Depois de 90 dias", "valor": "apagados de vez"},
            {
                "codigo": "contratos",
                "rotulo": "Contratos dos seus clientes",
                "valor": "continuam válidos",
            },
        ],
        "acesso_ate": datas.acesso_ate,
        "cancelada_em": datas.cancelada_em,
        "apagar_em": datas.apagar_em,
        "confirmacao": {"nome": empresa.nome_exibicao},
        "exportar": {"texto": TEXTO_DO_EXPORTAR},
    }


def planos_da_assinatura(empresa: Empresa | None = None) -> dict[str, Any]:
    """`GET /api/assinatura/planos/`: os planos ativos e o atual (PLT-05), com o preço de tabela,
    os textos da PLT-11 e se o uso cabe (PLT-04). A comparação é no ciclo atual (CA-ASS-18)."""
    empresa = empresa or empresa_atual()
    empresa = Empresa.objects.select_related("plano").get(pk=empresa.pk)
    atual = empresa.plano
    uso = UsoEmpresa.objects.filter(empresa_id=empresa.pk).first() or UsoEmpresa()
    planos = Plano.objects.filter(Q(ativo=True) | Q(pk=empresa.plano_id)).order_by("ordem", "id")
    resultados = []
    for plano in planos:
        e_atual = atual is not None and plano.pk == atual.pk
        excede = {} if e_atual else excede_no_plano(empresa, plano, uso)
        mudanca = None
        if not e_atual and atual is not None:
            mudanca = "upgrade" if plano_acima(plano, atual) else "downgrade"
        item: dict[str, Any] = {
            "id": plano.pk,
            "nome": plano.nome,
            "ordem": plano.ordem,
            "atual": e_atual,
            "preco_mensal_centavos": plano.preco_mensal_centavos,
            "preco_anual_centavos": plano.preco_anual_centavos,
            "limite_veiculos": plano.limite_veiculos,
            "limite_filiais": plano.limite_filiais,
            "limite_usuarios": plano.limite_usuarios,
            "itens": list(catalogo.textos(plano.nome).inclui),
            "mudanca": mudanca,
            "cabe": not excede,
            "excede": excede,
        }
        if e_atual:
            item["preco_contratado_centavos"] = empresa.preco_contratado_centavos
        resultados.append(item)
    return {"ciclo_atual": empresa.ciclo, "resultados": resultados}


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
        # Chamados e ações sobre a empresa são da fase 2.
        "chamados_abertos": 0,
        "suporte_bloqueado": empresa.suporte_bloqueado,
        "faturas_recentes": faturas_recentes(empresa),
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


# --- Faturas da assinatura (PLT-14; T-185 parte 2) ---


def faturas_da_empresa(empresa: Empresa, status: str | None = None) -> QuerySet[FaturaAssinatura]:
    """Sempre filtradas pela empresa da requisição: `FAT-0001` existe em todas (T-189, item 7)."""
    faturas = FaturaAssinatura.objects.filter(empresa_id=empresa.pk).select_related("plano")
    return faturas.filter(status=status) if status else faturas


def _situacao_da_fatura(fatura: FaturaAssinatura, sem_forma: bool, hoje: date) -> dict[str, str]:
    """A primeira que valer, na ordem do contrato (PLT-02, PLT-14)."""
    if fatura.status == StatusFatura.PAGA:
        pago = timezone.localtime(fatura.pago_em).date() if fatura.pago_em else hoje
        return {"codigo": "paga", "rotulo": f"Paga em {dia_e_mes(pago)}", "tom": "sucesso"}
    if fatura.status == StatusFatura.CANCELADA:
        return {"codigo": "cancelada", "rotulo": "Cancelada", "tom": "neutro"}
    if fatura.cartao_recusado_em is not None:
        rotulo = (
            "Cartão recusado · pague por Pix ou boleto"
            if fatura.tentativas_cartao >= TENTATIVAS_DO_CARTAO
            else "Cartão recusado · nova tentativa amanhã"
        )
        return {"codigo": "cartao_recusado", "rotulo": rotulo, "tom": "perigo"}
    if fatura.status == StatusFatura.ATRASADA:
        dias = max(1, (hoje - fatura.vencimento).days)
        rotulo = f"{dias} {'dia' if dias == 1 else 'dias'} atrasada"
        return {"codigo": "atrasada", "rotulo": rotulo, "tom": "perigo"}
    if sem_forma:
        return {"codigo": "sem_forma", "rotulo": "Sem forma de pagamento", "tom": "alerta"}
    rotulo = (
        "Vence hoje" if fatura.vencimento == hoje else f"Vence em {dia_e_mes(fatura.vencimento)}"
    )
    return {"codigo": "aguardando", "rotulo": rotulo, "tom": "info"}


@dataclass(frozen=True)
class ContextoDasFaturas:
    """O que vale para todas as linhas da página: lido uma vez."""

    empresa: Empresa
    sem_forma: bool
    escreve: bool
    hoje: date


def contexto_das_faturas(empresa: Empresa, usuario: Any) -> ContextoDasFaturas:
    forma = FormaPagamentoAssinatura.objects.filter(empresa_id=empresa.pk).first()
    escreve = (
        getattr(usuario, "perfil", None) == PERFIL_ADMINISTRADOR
        and not getattr(usuario, "e_suporte", False)
        and empresa.status in STATUS_QUE_PAGAM
    )
    return ContextoDasFaturas(empresa, not (forma and forma.forma), escreve, relogio.hoje())


def _pode_pagar(fatura: FaturaAssinatura, contexto: ContextoDasFaturas) -> bool:
    """`aberta` ou `atrasada` e o estado permite. Sem forma, a `aberta` que ainda não venceu não
    tem "Pagar"; a `atrasada` e qualquer fatura da `suspensa` têm (o corpo escolhe o meio)."""
    if not contexto.escreve or fatura.status not in (StatusFatura.ABERTA, StatusFatura.ATRASADA):
        return False
    if not contexto.sem_forma or contexto.empresa.status == Empresa.Status.SUSPENSA:
        return True
    return fatura.status == StatusFatura.ATRASADA or fatura.vencimento < contexto.hoje


def item_da_fatura(fatura: FaturaAssinatura, contexto: ContextoDasFaturas) -> dict[str, Any]:
    paga = fatura.status == StatusFatura.PAGA
    return {
        "tipo": "fatura",
        "codigo": fatura.codigo,
        "vencimento": fatura.vencimento,
        "descricao": fatura.descricao,
        "periodo": {"inicio": fatura.periodo_inicio, "fim": fatura.periodo_fim},
        "valor_centavos": fatura.valor_centavos,
        "status": fatura.status,
        "forma": fatura.forma or None,
        "pago_em": fatura.pago_em,
        "situacao": _situacao_da_fatura(fatura, contexto.sem_forma, contexto.hoje),
        "acoes": {
            "pagar": _pode_pagar(fatura, contexto),
            "recibo": paga,
            "nota_fiscal": paga and fatura.nota_situacao == SituacaoNota.EMITIDA,
        },
    }


def linha_do_teste(empresa: Empresa) -> dict[str, Any] | None:
    """A linha do teste grátis no fim da lista: não é uma fatura (PLT-01, PLT-14)."""
    if empresa.teste_inicio is None or empresa.teste_fim is None:
        return None
    dias = (empresa.teste_fim - empresa.teste_inicio).days
    ativo = empresa.status == Empresa.Status.EM_TESTE and relogio.hoje() <= empresa.teste_fim
    return {
        "tipo": "teste",
        "codigo": None,
        "vencimento": empresa.teste_inicio,
        "descricao": f"Teste grátis de {dias} dias",
        "periodo": {"inicio": empresa.teste_inicio, "fim": empresa.teste_fim},
        "valor_centavos": 0,
        "status": None,
        "forma": None,
        "pago_em": None,
        "situacao": (
            {"codigo": "teste_ativo", "rotulo": "Ativo", "tom": "info"}
            if ativo
            else {"codigo": "teste_concluido", "rotulo": "Concluído", "tom": "neutro"}
        ),
        "acoes": {"pagar": False, "recibo": False, "nota_fiscal": False},
    }


def cobranca_da_fatura(fatura: FaturaAssinatura) -> dict[str, Any] | None:
    """A cobrança viva no parceiro, para pagar. Só na resposta ao administrador; nunca na
    auditoria (T-189, item 8)."""
    if not fatura.cobranca_externa_id:
        return None
    forma = {
        "cartao_link": "cartao",
        "cartao": "cartao",
        "pix": "pix",
        "pix_auto": "pix",
        "boleto": "boleto",
    }.get(fatura.cobranca_tipo)
    return {
        "forma": forma,
        "linha_digitavel": fatura.cobranca_linha_digitavel or None,
        "url_boleto": fatura.cobranca_boleto_url or None,
        "pix_copia_e_cola": fatura.cobranca_pix_copia_e_cola or None,
        "url_pagina": fatura.cobranca_url_pagina or None,
        "vencimento": fatura.vencimento,
    }


def nota_fiscal_da_fatura(fatura: FaturaAssinatura) -> dict[str, Any] | None:
    """PLT-15: nula antes do pedido e com a emissão desligada. O motivo do erro fica com a
    equipe (Django Admin)."""
    if not fatura.nota_situacao:
        return None
    return {
        "situacao": fatura.nota_situacao,
        "numero": fatura.nota_numero or None,
        "url": fatura.nota_url or None,
    }


def detalhe_da_fatura(fatura: FaturaAssinatura, contexto: ContextoDasFaturas) -> dict[str, Any]:
    return {
        **item_da_fatura(fatura, contexto),
        "cobranca": cobranca_da_fatura(fatura),
        "recibo_url": (fatura.recibo_url or None) if fatura.status == StatusFatura.PAGA else None,
        "nota_fiscal": nota_fiscal_da_fatura(fatura),
    }


# --- Módulos do plano e ramo (PLT-12, ADR 0024, itens 2 e 10) ---

ATIVIDADES = ("aluga", "vende", "ambos")
# O recurso de operação que cada lado do ramo liga.
RECURSO_DA_ATIVIDADE = {"aluga": Recurso.LOCACOES_VISTORIA, "vende": Recurso.VENDAS_COMISSOES}


def recursos_para(plano: Plano | None, atividade: str) -> frozenset[str]:
    """`Plano.recursos` menos o módulo de operação que a atividade não usa. Função pura."""
    recursos = set(plano.recursos if plano is not None else [])
    for lado, recurso in RECURSO_DA_ATIVIDADE.items():
        if atividade not in (lado, "ambos"):
            recursos.discard(recurso)
    return frozenset(recursos)


def atividades_aceitas(plano: Plano | None) -> tuple[str, ...]:
    """As atividades com pelo menos um módulo de operação no plano (Essencial: aluga e ambos)."""
    operacao = set(RECURSO_DA_ATIVIDADE.values())
    return tuple(a for a in ATIVIDADES if recursos_para(plano, a) & operacao)


def recursos_da_empresa(empresa: Empresa | None = None) -> frozenset[str]:
    """Os recursos ligados na empresa: os do plano atual com o ramo guardado. Nada é guardado."""
    empresa = empresa or empresa_atual()
    return recursos_para(empresa.plano, comum_empresa.atividade())


def primeiro_plano_com(recurso: str) -> Plano | None:
    """O plano ativo mais baixo do catálogo que liga `recurso` (o aviso de "vende")."""
    for plano in Plano.objects.filter(ativo=True).order_by("ordem", "preco_mensal_centavos"):
        if recurso in (plano.recursos or []):
            return plano
    return None
