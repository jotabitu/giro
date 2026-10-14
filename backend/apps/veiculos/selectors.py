"""Leituras dos veículos, categorias e preços (VEI-06, LOC-01, LOC-15).

Interface para os outros apps (contrato de veículos): `preco_vigente(categoria, data)` e
`ocupacao(veiculo)`. Os blocos `locacao_atual`, `manutencao` e `indicadores_financeiros` vêm de
`locacoes`, `manutencao` e `financeiro` pelo registro de leituras (ADR 0015).
"""

from collections.abc import Iterable
from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.db.models import Count, Q, QuerySet
from django.utils import timezone

from comum import arquivos, leituras, relogio
from comum.permissoes import filiais_permitidas

from .models import (
    FORA_DA_FROTA,
    TRANSICOES_VEICULO,
    Categoria,
    DocumentoVeiculo,
    Extra,
    HistoricoStatusVeiculo,
    PrecoCategoria,
    StatusVeiculo,
    TipoVeiculo,
    Veiculo,
)
from .services import (
    SituacaoDocumento,
    normalizar_chassi,
    normalizar_placa,
    situacao_do_documento,
)

S = StatusVeiculo
ALVO = "veiculos.Veiculo"
ALVO_FILIAL = "filiais.Filial"
PERIODO_OCUPACAO_DIAS = 90
# Dias que não contam como "na frota" para a ocupação (VEI-06).
FORA_DA_OCUPACAO = frozenset({S.A_VENDA, S.VENDIDO, S.BAIXADO})
GESTAO = frozenset({"administrador", "gerente"})
LEEM_KM = frozenset({"administrador", "gerente", "vistoriador"})
TOM = {
    S.DISPONIVEL: "sucesso",
    S.RESERVADO: "info",
    S.ALUGADO: "solido",
    S.EM_MANUTENCAO: "alerta",
    S.INDISPONIVEL: "neutro",
    S.A_VENDA: "neutro",
    S.VENDIDO: "neutro",
    S.BAIXADO: "neutro",
}
GRAVIDADE = {"perigo": 3, "alerta": 2, "info": 1}
ORDENS = {"placa": "placa", "-km_atual": "-km_atual", "modelo": "modelo"}


# --- Preço (LOC-01, LOC-15) ---


def preco_vigente(categoria: Categoria | int, data: date) -> PrecoCategoria | None:
    """O preço de maior `vigente_desde <= data`."""
    categoria_id = categoria if isinstance(categoria, int) else categoria.pk
    return (
        PrecoCategoria.objects.filter(categoria_id=categoria_id, vigente_desde__lte=data)
        .order_by("-vigente_desde")
        .first()
    )


def proximo_preco(categoria: Categoria, data: date) -> PrecoCategoria | None:
    return categoria.precos.filter(vigente_desde__gt=data).order_by("vigente_desde").first()


def valores_do_preco(preco: PrecoCategoria | None, com_data: bool = False) -> dict[str, Any] | None:
    if preco is None:
        return None
    valores: dict[str, Any] = {"vigente_desde": preco.vigente_desde} if com_data else {}
    return {
        **valores,
        "diaria_centavos": preco.diaria_centavos,
        "semanal_centavos": preco.semanal_centavos,
        "mensal_centavos": preco.mensal_centavos,
        "caucao_centavos": preco.caucao_centavos,
    }


def precos_vigentes(categorias_ids: set[int], data: date) -> dict[int, PrecoCategoria]:
    """Um preço por categoria, numa query, para a lista."""
    vigentes: dict[int, PrecoCategoria] = {}
    for preco in PrecoCategoria.objects.filter(
        categoria_id__in=categorias_ids, vigente_desde__lte=data
    ).order_by("categoria_id", "-vigente_desde"):
        vigentes.setdefault(preco.categoria_id, preco)
    return vigentes


def historico_de_precos(categoria: Categoria) -> list[dict[str, Any]]:
    return [
        {
            **(valores_do_preco(preco, com_data=True) or {}),
            "alterado_por": preco.alterado_por.nome if preco.alterado_por else None,
            "alterado_em": preco.criado_em,
        }
        for preco in categoria.precos.select_related("alterado_por").order_by("-vigente_desde")
    ]


def mudancas_de_preco() -> list[dict[str, Any]]:
    """`GET /api/precos/historico/`: cada campo que mudou, de uma vigência para a seguinte."""
    linhas: list[dict[str, Any]] = []
    anterior: dict[int, PrecoCategoria] = {}
    precos = PrecoCategoria.objects.select_related("categoria", "alterado_por").order_by(
        "categoria_id", "vigente_desde"
    )
    for preco in precos:
        antes = anterior.get(preco.categoria_id)
        for campo in ("diaria_centavos", "semanal_centavos", "mensal_centavos", "caucao_centavos"):
            valor_antes = getattr(antes, campo) if antes else None
            if valor_antes == getattr(preco, campo):
                continue
            linhas.append(
                {
                    "categoria": {"id": preco.categoria_id, "nome": preco.categoria.nome},
                    "vigente_desde": preco.vigente_desde,
                    "campo": campo,
                    "antes_centavos": valor_antes,
                    "depois_centavos": getattr(preco, campo),
                    "alterado_por": preco.alterado_por.nome if preco.alterado_por else None,
                    "alterado_em": preco.criado_em,
                }
            )
        anterior[preco.categoria_id] = preco
    linhas.sort(key=lambda linha: (linha["vigente_desde"], linha["alterado_em"]), reverse=True)
    return linhas


# --- Categorias ---


def categorias(
    filial_id: int | None = None, tipo_veiculo: str | None = None, ativo: str | None = None
) -> QuerySet[Categoria]:
    """As da empresa e, com `filial_id`, as dessa filial."""
    qs = Categoria.objects.annotate(
        _veiculos=Count("veiculos", filter=~Q(veiculos__status__in=FORA_DA_FROTA))
    )
    if filial_id is not None:
        qs = qs.filter(Q(filial__isnull=True) | Q(filial_id=filial_id))
    if tipo_veiculo in TipoVeiculo.values:
        qs = qs.filter(tipo_veiculo=tipo_veiculo)
    if ativo in ("true", "false"):
        qs = qs.filter(ativo=ativo == "true")
    return qs.order_by("nome", "id")


def modelos_resumo(categoria: Categoria) -> str:
    modelos = (
        categoria.veiculos.exclude(status__in=FORA_DA_FROTA)
        .order_by("modelo")
        .values_list("modelo", flat=True)
        .distinct()
    )
    return ", ".join(modelos)


def representacao_categoria(categoria: Categoria) -> dict[str, Any]:
    hoje = relogio.hoje()
    veiculos = getattr(categoria, "_veiculos", None)
    if veiculos is None:
        veiculos = categoria.veiculos.exclude(status__in=FORA_DA_FROTA).count()
    return {
        "id": categoria.pk,
        "nome": categoria.nome,
        "tipo_veiculo": categoria.tipo_veiculo,
        "filial": (
            {"id": categoria.filial.pk, "nome": categoria.filial.nome} if categoria.filial else None
        ),
        "ativo": categoria.ativo,
        "modelos_resumo": modelos_resumo(categoria),
        "veiculos": veiculos,
        "preco_vigente": valores_do_preco(preco_vigente(categoria, hoje), com_data=True),
        "proximo_preco": valores_do_preco(proximo_preco(categoria, hoje), com_data=True),
    }


def extras(ativo: str | None = None) -> QuerySet[Extra]:
    """Só os ativos (a escolha na locação); `?ativo=false` mostra os desativados."""
    return Extra.objects.filter(ativo=ativo != "false").order_by("nome", "id")


def representacao_extra(extra: Extra) -> dict[str, Any]:
    return {
        "id": extra.pk,
        "nome": extra.nome,
        "valor_centavos": extra.valor_centavos,
        "cobranca": extra.cobranca,
        "ativo": extra.ativo,
    }


# --- Frota ---


def no_escopo(usuario: Any) -> QuerySet[Veiculo]:
    """Veículos das filiais da pessoa (USR-07): fora delas, a ficha responde 404."""
    return Veiculo.objects.filter(filial_id__in=filiais_permitidas(usuario))


def filtrar(
    qs: QuerySet[Veiculo],
    *,
    status: str | None = None,
    categoria: str | None = None,
    busca: str | None = None,
) -> QuerySet[Veiculo]:
    """`vendido` e `baixado` só aparecem com o filtro explícito (histórico)."""
    qs = qs.filter(status=status) if status in S.values else qs.exclude(status__in=FORA_DA_FROTA)
    if categoria and categoria.isdigit():
        qs = qs.filter(categoria_id=int(categoria))
    texto = (busca or "").strip()
    if texto:
        placa = normalizar_placa(texto)
        chassi = normalizar_chassi(texto)
        filtro = Q(modelo__icontains=texto) | Q(marca__icontains=texto)
        if placa:
            filtro |= Q(placa__icontains=placa)
        if chassi:
            filtro |= Q(chassi__icontains=chassi)
        qs = qs.filter(filtro)
    return qs


def do_tipo(qs: QuerySet[Veiculo], tipo_veiculo: str | None) -> QuerySet[Veiculo]:
    if tipo_veiculo in TipoVeiculo.values:
        return qs.filter(categoria__tipo_veiculo=tipo_veiculo)
    return qs


def contagens(qs: QuerySet[Veiculo]) -> dict[str, int]:
    """Das abas da Frota: seguem filial e tipo, nunca o status."""
    na_frota = qs.exclude(status__in=FORA_DA_FROTA)
    por_status = dict(
        na_frota.order_by()
        .values_list("status")
        .annotate(total=Count("id"))
        .values_list("status", "total")
    )
    por_tipo = dict(
        na_frota.order_by()
        .values_list("categoria__tipo_veiculo")
        .annotate(total=Count("id"))
        .values_list("categoria__tipo_veiculo", "total")
    )
    return {
        "todos": sum(por_status.values()),
        **{
            status: por_status.get(status, 0)
            for status in (
                S.DISPONIVEL,
                S.ALUGADO,
                S.RESERVADO,
                S.EM_MANUTENCAO,
                S.A_VENDA,
                S.INDISPONIVEL,
            )
        },
        "motos": por_tipo.get(TipoVeiculo.MOTO, 0),
        "carros": por_tipo.get(TipoVeiculo.CARRO, 0),
    }


def acoes(veiculo: Veiculo, usuario: Any) -> dict[str, bool]:
    """Perfil, status e a tabela de transições: o frontend mostra só o que vier `true`."""
    perfil = getattr(usuario, "perfil", "")
    gestao = perfil in GESTAO
    status = veiculo.status
    na_frota = status not in FORA_DA_FROTA
    pode_ir = TRANSICOES_VEICULO.get(status, set())
    return {
        "editar": gestao and na_frota,
        "colocar_a_venda": gestao and status == S.DISPONIVEL,
        "voltar_para_frota": gestao and status == S.A_VENDA,
        "bloquear": gestao and status == S.DISPONIVEL,
        "desbloquear": gestao and status == S.INDISPONIVEL,
        "transferir": gestao and status == S.DISPONIVEL,
        "baixar": perfil == "administrador" and S.BAIXADO in pode_ir,
        "registrar_km": perfil in LEEM_KM and na_frota,
        # O vistoriador pede a correção, que vai para a aprovação do gerente (APR-06).
        "corrigir_km": perfil in LEEM_KM and na_frota,
    }


def _situacao(veiculo: Veiculo, blocos: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Base no status; o `alerta` mais grave de um bloco sobrepõe (ADR 0015)."""
    situacao = {
        "codigo": veiculo.status,
        "rotulo": S(veiculo.status).label,
        "tom": TOM[S(veiculo.status)],
    }
    alertas = [
        bloco["alerta"]
        for bloco in blocos.values()
        if isinstance(bloco.get("alerta"), dict) and bloco["alerta"].get("tom") in GRAVIDADE
    ]
    if alertas:
        alerta = max(alertas, key=lambda a: GRAVIDADE[a["tom"]])
        situacao = {
            "codigo": alerta.get("codigo", veiculo.status),
            "rotulo": alerta["rotulo"],
            "tom": alerta["tom"],
        }
    return situacao


def representacao(
    veiculo: Veiculo,
    usuario: Any,
    *,
    precos: dict[int, PrecoCategoria] | None = None,
    documentos: dict[int, dict[str, Any] | None] | None = None,
    detalhe: bool = False,
) -> dict[str, Any]:
    if precos is None:
        precos = precos_vigentes({veiculo.categoria_id}, relogio.hoje())
    if documentos is None:
        documentos = resumos_de_documentos({veiculo.pk}, relogio.hoje())
    gestao = getattr(usuario, "perfil", "") in GESTAO
    blocos = leituras.blocos(ALVO, veiculo)
    dados: dict[str, Any] = {
        "id": veiculo.pk,
        "placa": veiculo.placa,
        "chassi": veiculo.chassi,
        "renavam": veiculo.renavam or None,
        "marca": veiculo.marca,
        "modelo": veiculo.modelo,
        "ano_fabricacao": veiculo.ano_fabricacao,
        "ano_modelo": veiculo.ano_modelo,
        "cor": veiculo.cor,
        "tipo_veiculo": veiculo.categoria.tipo_veiculo,
        "categoria": {"id": veiculo.categoria_id, "nome": veiculo.categoria.nome},
        "filial": {"id": veiculo.filial_id, "nome": veiculo.filial.nome},
        "status": veiculo.status,
        "motivo_status": veiculo.motivo_status or None,
        "km_atual": veiculo.km_atual,
        "km_atualizado_em": veiculo.km_atualizado_em,
        "capacidade_tanque_litros": veiculo.capacidade_tanque_litros,
        "preco_vigente": valores_do_preco(precos.get(veiculo.categoria_id)),
        "valor_venda_centavos": veiculo.valor_venda_centavos,
        "referencia_fipe_centavos": veiculo.referencia_fipe_centavos,
        # Dados de compra só para administrador e gerente.
        "valor_compra_centavos": veiculo.valor_compra_centavos if gestao else None,
        "data_compra": veiculo.data_compra if gestao else None,
        "entrou_na_frota_em": veiculo.entrou_na_frota_em,
        "situacao": _situacao(veiculo, blocos),
        "locacao_atual": blocos.get("locacao_atual"),
        "manutencao": blocos.get("manutencao"),
        "documentos_resumo": documentos.get(veiculo.pk),
        "acoes": acoes(veiculo, usuario),
    }
    if detalhe:
        dados["indicadores_financeiros"] = blocos.get("indicadores_financeiros")
        dados["ocupacao"] = ocupacao(veiculo)
        dados["historico_status"] = historico_status(veiculo)
    return dados


# Blocos que só têm dinheiro: saem inteiros para quem não vê valores.
BLOCOS_DE_VALOR = frozenset({"preco_vigente", "proximo_preco", "indicadores_financeiros"})


def ve_valores(usuario: Any) -> bool:
    """D-25, USR-09: o vistoriador não recebe valor em dinheiro (preço, venda, compra)."""
    return getattr(usuario, "perfil", "") != "vistoriador"


def sem_valores(dados: Any) -> Any:
    """Sem nenhum campo `_centavos` e sem os blocos de preço. Aplicado depois do serializer, que
    preencheria com `null` o campo que falta."""
    if isinstance(dados, dict):
        return {
            chave: sem_valores(valor)
            for chave, valor in dados.items()
            if not chave.endswith("_centavos")
            and chave not in BLOCOS_DE_VALOR
            and chave != "data_compra"
        }
    if isinstance(dados, list):
        return [sem_valores(item) for item in dados]
    return dados


def historico_status(veiculo: Veiculo) -> list[dict[str, Any]]:
    return [
        {
            "de": item.de or None,
            "para": item.para,
            "em": item.em,
            "origem_tipo": item.origem_tipo,
            "origem_codigo": item.origem_codigo or None,
            "motivo": item.motivo or None,
        }
        for item in veiculo.historico.order_by("-em", "-id")
    ]


# --- Ocupação (VEI-06) ---


def _tempos(
    eventos: list[tuple[datetime, str]], inicio: datetime, fim: datetime
) -> tuple[timedelta, timedelta]:
    """(alugado, na frota) entre `inicio` e `fim`, a partir das mudanças de status em ordem."""
    alugado = timedelta(0)
    na_frota = timedelta(0)
    for indice, (em, para) in enumerate(eventos):
        de = max(em, inicio)
        ate = min(eventos[indice + 1][0], fim) if indice + 1 < len(eventos) else fim
        if ate <= de or para in FORA_DA_OCUPACAO:
            continue
        na_frota += ate - de
        if para == S.ALUGADO:
            alugado += ate - de
    return alugado, na_frota


def _pct(alugado: timedelta, na_frota: timedelta) -> str:
    if not na_frota:
        return "0.00"
    valor = Decimal(int(alugado.total_seconds()) * 100) / Decimal(int(na_frota.total_seconds()))
    return str(valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _eventos(veiculo_ids: list[int], fim: datetime) -> dict[int, list[tuple[datetime, str]]]:
    por_veiculo: dict[int, list[tuple[datetime, str]]] = {pk: [] for pk in veiculo_ids}
    for veiculo_id, em, para in (
        HistoricoStatusVeiculo.objects.filter(veiculo_id__in=veiculo_ids, em__lte=fim)
        .order_by("veiculo_id", "em", "id")
        .values_list("veiculo_id", "em", "para")
    ):
        por_veiculo[veiculo_id].append((em, para))
    return por_veiculo


def ocupacao(veiculo: Veiculo, dias: int = PERIODO_OCUPACAO_DIAS) -> dict[str, Any]:
    """Dias alugado ÷ dias na frota nos últimos `dias`, sem os dias à venda, vendido ou
    baixado. Quem entrou na frota no meio do período conta só desde a entrada."""
    fim = relogio.agora()
    eventos = _eventos([veiculo.pk], fim)[veiculo.pk]
    return {"pct": _pct(*_tempos(eventos, fim - timedelta(days=dias), fim)), "periodo_dias": dias}


def ocupacao_da_frota(filial_id: int | Iterable[int], dias: int = PERIODO_OCUPACAO_DIAS) -> str:
    """Média ponderada pelos dias (VEI-06): soma dos dias alugados ÷ soma dos dias na frota.
    Uma filial ou várias (o painel com "Todas as filiais")."""
    fim = relogio.agora()
    inicio = fim - timedelta(days=dias)
    filiais = [filial_id] if isinstance(filial_id, int) else list(filial_id)
    ids = list(Veiculo.objects.filter(filial_id__in=filiais).values_list("pk", flat=True))
    alugado = timedelta(0)
    na_frota = timedelta(0)
    for eventos in _eventos(ids, fim).values():
        a, f = _tempos(eventos, inicio, fim)
        alugado += a
        na_frota += f
    return _pct(alugado, na_frota)


def da_frota(filiais: Iterable[int]) -> QuerySet[Veiculo]:
    """Veículos das filiais do escopo do painel (`relatorios`); `contagens` tira os de fora da
    frota."""
    return Veiculo.objects.filter(filial_id__in=list(filiais))


def alugados_em(filiais: Iterable[int], momento: datetime) -> int:
    """Veículos das filiais cujo último status até `momento` era `alugado` (histórico, VEI-06).
    Base da tendência "6 a mais esta semana" do painel."""
    ids = list(da_frota(filiais).values_list("pk", flat=True))
    return sum(
        1 for eventos in _eventos(ids, momento).values() if eventos and eventos[-1][1] == S.ALUGADO
    )


def frota_ativa_em(dia: date, filiais: Iterable[int]) -> int:
    """Veículos das filiais fora de `vendido` e `baixado` no fim de `dia` em America/Sao_Paulo,
    pelo último status do histórico (FIN-16, despesa por veículo). Cadastrado depois do dia não
    conta; vendido ou baixado depois do dia conta. A filial é a atual do veículo."""
    fim = timezone.make_aware(datetime.combine(dia + timedelta(days=1), time.min))
    ultimo: dict[int, str] = {}
    for veiculo_id, para in (
        HistoricoStatusVeiculo.objects.filter(veiculo__filial_id__in=list(filiais), em__lt=fim)
        .order_by("veiculo_id", "em", "id")
        .values_list("veiculo_id", "para")
    ):
        ultimo[veiculo_id] = para
    return sum(1 for para in ultimo.values() if para not in FORA_DA_FROTA)


# --- Fornecido a filiais (ADR 0015) ---


def veiculos_em_operacao(filial_id: int) -> int:
    """Operação que impede desativar a filial (FIL-06): fora de `vendido` e `baixado`."""
    return int(
        Veiculo.objects.filter(filial_id=filial_id).exclude(status__in=FORA_DA_FROTA).count()
    )


def anotar_indicadores(queryset: QuerySet[Any]) -> QuerySet[Any]:
    return queryset  # o número sai em `montar_indicadores`, uma query por filial da página


def montar_indicadores(filial: Any) -> dict[str, Any]:
    return {
        "veiculos": veiculos_em_operacao(filial.pk),
        "ocupacao_pct": ocupacao_da_frota(filial.pk),
    }


def contar_veiculos_do_plano() -> int:
    """Uso do plano (PLT-03): os veículos fora de `vendido` e `baixado`."""
    return int(Veiculo.objects.exclude(status__in=FORA_DA_FROTA).count())


# --- Documentos (VEI-03, AUD-05) ---

# Da pior para a melhor: o resumo da Frota mostra a pior.
ORDEM_DAS_SITUACOES = (
    SituacaoDocumento.VENCIDO,
    SituacaoDocumento.VENCE_EM_BREVE,
    SituacaoDocumento.EM_DIA,
)


def resumos_de_documentos(veiculo_ids: set[int], hoje: date) -> dict[int, dict[str, Any] | None]:
    """`{veiculo_id: {"pior_situacao": ...}}` dos documentos ativos; sem documento, `None`."""
    piores: dict[int, str] = {}
    validades = DocumentoVeiculo.ativos.filter(veiculo_id__in=veiculo_ids).values_list(
        "veiculo_id", "validade"
    )
    for veiculo_id, validade in validades:
        situacao, _ = situacao_do_documento(validade, hoje)
        atual = piores.get(veiculo_id)
        if atual is None or ORDEM_DAS_SITUACOES.index(situacao) < ORDEM_DAS_SITUACOES.index(atual):
            piores[veiculo_id] = situacao
    return {
        veiculo_id: {"pior_situacao": piores[veiculo_id]} if veiculo_id in piores else None
        for veiculo_id in veiculo_ids
    }


def documentos(veiculo: Veiculo, *, historico: bool = False) -> QuerySet[DocumentoVeiculo]:
    """Os ativos (um por tipo) ou, no histórico, todos."""
    qs = DocumentoVeiculo.objects if historico else DocumentoVeiculo.ativos
    return qs.filter(veiculo=veiculo).order_by("tipo", "-validade", "-id")


def representacao_documento(documento: DocumentoVeiculo, hoje: date) -> dict[str, Any]:
    """`arquivo.url` é assinada e vale 15 minutos; cada leitura gera outra (AUD-05)."""
    situacao, dias = situacao_do_documento(documento.validade, hoje)
    arquivo = None
    if documento.arquivo:
        assinada = arquivos.url_assinada(documento.arquivo.name)
        arquivo = {
            "nome": documento.arquivo_nome,
            "url": assinada.url,
            "url_expira_em": assinada.expira_em,
        }
    return {
        "id": documento.pk,
        "tipo": documento.tipo,
        "validade": documento.validade,
        "situacao": situacao,
        "dias_para_vencer": dias,
        "ativo": documento.ativo,
        "arquivo": arquivo,
    }
