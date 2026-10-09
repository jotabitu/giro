"""O que `locacoes` fornece às listas dos apps de cima (ADR 0015), registrado no `ready()`.

- `veiculos.Veiculo`: bloco `locacao_atual` (com o alerta "Atrasado" na devolução atrasada).
- `clientes.Cliente`: blocos `locacao_atual` e `ultima_locacao`, filtro `com_locacao` e o
  contador `locacao_aberta` (CLI-09).
- `filiais.Filial`: `locacoes_ativas` no bloco `indicadores` e o contador `locacoes` (FIL-06).
- `veiculos.Categoria`: contador `locacoes_em_andamento` (LOC-15, aviso do preço novo).
"""

from datetime import date
from typing import Any

from django.db.models import Count, IntegerField, OuterRef, QuerySet, Subquery
from django.db.models.functions import Coalesce
from django.utils import timezone

from comum import leituras, relogio

from .models import ABERTAS, Locacao, Periodicidade, StatusLocacao

S = StatusLocacao
VEICULO = "veiculos.Veiculo"
CLIENTE = "clientes.Cliente"
FILIAL = "filiais.Filial"
CATEGORIA = "veiculos.Categoria"
CAMPOS = {
    "id": "pk",
    "codigo": "codigo",
    "status": "status",
    "inicio": "inicio",
    "fim": "fim_previsto",
    "cliente_nome": "cliente__nome",
    "veiculo_modelo": "veiculo__modelo",
    "periodicidade": "periodicidade",
}


def _abertas_de(campo: str) -> QuerySet[Locacao]:
    return Locacao.objects.filter(status__in=ABERTAS, **{campo: OuterRef("pk")}).order_by("-id")


def _anotar_atual(queryset: QuerySet[Any], campo: str) -> QuerySet[Any]:
    abertas = _abertas_de(campo)
    return queryset.annotate(  # type: ignore[no-any-return]
        **{f"loc_{nome}": Subquery(abertas.values(origem)[:1]) for nome, origem in CAMPOS.items()}
    )


def _atual(objeto: Any, campo: str) -> dict[str, Any] | None:
    """As anotações, ou uma consulta quando o objeto veio sem elas (ficha)."""
    if hasattr(objeto, "loc_id"):
        if objeto.loc_id is None:
            return None
        return {nome: getattr(objeto, f"loc_{nome}") for nome in CAMPOS}
    linha = (
        Locacao.objects.filter(status__in=ABERTAS, **{campo: objeto.pk})
        .order_by("-id")
        .values(*CAMPOS.values())
        .first()
    )
    return {nome: linha[origem] for nome, origem in CAMPOS.items()} if linha else None


def _dias(fim: Any) -> int:
    return max(0, (relogio.hoje() - timezone.localdate(fim)).days)


# --- veiculos.Veiculo ---


def anotar_veiculo(queryset: QuerySet[Any]) -> QuerySet[Any]:
    return _anotar_atual(queryset, "veiculo")


def montar_veiculo(veiculo: Any) -> dict[str, Any] | None:
    atual = _atual(veiculo, "veiculo")
    if atual is None:
        return None
    bloco: dict[str, Any] = {
        "id": atual["id"],
        "codigo": atual["codigo"],
        "status": atual["status"],
        "cliente_nome": atual["cliente_nome"],
        "inicio": atual["inicio"],
        "fim_previsto": atual["fim"],
    }
    if atual["status"] == S.DEVOLUCAO_ATRASADA:
        bloco["alerta"] = {"codigo": "atrasado", "rotulo": "Atrasado", "tom": "perigo"}
    return bloco


# --- clientes.Cliente ---


def anotar_cliente(queryset: QuerySet[Any]) -> QuerySet[Any]:
    return _anotar_atual(queryset, "cliente")


def _detalhe(atual: dict[str, Any]) -> str:
    if atual["status"] == S.DEVOLUCAO_ATRASADA:
        return f"{_dias(atual['fim'])} dias de atraso"
    if atual["status"] == S.AGUARDANDO_RETIRADA:
        return "aguardando retirada"
    if timezone.localdate(atual["fim"]) == relogio.hoje():
        return "devolve hoje"
    return Periodicidade(atual["periodicidade"]).label.lower()


def montar_cliente_atual(cliente: Any) -> dict[str, Any] | None:
    atual = _atual(cliente, "cliente")
    if atual is None:
        return None
    return {
        "id": atual["id"],
        "codigo": atual["codigo"],
        "veiculo": atual["veiculo_modelo"],
        "detalhe": _detalhe(atual),
        "valor_a_devolver_centavos": None,  # encerramento antecipado (LOC-13), T-091
        "alerta": "Devolução atrasada" if atual["status"] == S.DEVOLUCAO_ATRASADA else None,
    }


def montar_cliente_ultima(cliente: Any) -> dict[str, Any] | None:
    if _atual(cliente, "cliente") is not None:
        return None
    ultima = (
        Locacao.objects.filter(cliente_id=cliente.pk, status=S.ENCERRADA)
        .order_by("-devolvida_em", "-id")
        .values("codigo", "devolvida_em")
        .first()
    )
    if ultima is None:
        return None
    devolvida = ultima["devolvida_em"]
    encerrada_em: date | None = timezone.localdate(devolvida) if devolvida else None
    return {"codigo": ultima["codigo"], "encerrada_em": encerrada_em}


def com_locacao(queryset: QuerySet[Any]) -> QuerySet[Any]:
    return queryset.filter(pk__in=Locacao.objects.filter(status__in=ABERTAS).values("cliente_id"))


def locacao_aberta(cliente_id: int) -> int:
    return Locacao.objects.filter(cliente_id=cliente_id, status__in=ABERTAS).count()


# --- filiais.Filial ---


def anotar_filial(queryset: QuerySet[Any]) -> QuerySet[Any]:
    ativas = (
        Locacao.objects.filter(filial_id=OuterRef("pk"), status__in=(S.ATIVA, S.DEVOLUCAO_ATRASADA))
        .order_by()
        .values("filial_id")
        .annotate(n=Count("id"))
        .values("n")
    )
    return queryset.annotate(  # type: ignore[no-any-return]
        loc_ativas=Coalesce(Subquery(ativas, output_field=IntegerField()), 0)
    )


def montar_filial(filial: Any) -> dict[str, Any]:
    if hasattr(filial, "loc_ativas"):
        return {"locacoes_ativas": filial.loc_ativas}
    return {
        "locacoes_ativas": Locacao.objects.filter(
            filial_id=filial.pk, status__in=(S.ATIVA, S.DEVOLUCAO_ATRASADA)
        ).count()
    }


def locacoes_da_filial(filial_id: int) -> int:
    """Operação que impede desativar a filial (FIL-06)."""
    return Locacao.objects.filter(filial_id=filial_id, status__in=ABERTAS).count()


def locacoes_da_categoria(categoria_id: int) -> int:
    return Locacao.objects.filter(veiculo__categoria_id=categoria_id, status__in=ABERTAS).count()


def _sem_anotacao(queryset: QuerySet[Any]) -> QuerySet[Any]:
    return queryset


def registrar() -> None:
    leituras.registrar_anotacao(VEICULO, "locacao_atual", anotar_veiculo, montar_veiculo)
    leituras.registrar_anotacao(CLIENTE, "locacao_atual", anotar_cliente, montar_cliente_atual)
    # A anotação da locação atual já serve aos dois blocos do cliente.
    leituras.registrar_anotacao(CLIENTE, "ultima_locacao", _sem_anotacao, montar_cliente_ultima)
    leituras.registrar_filtro(CLIENTE, "com_locacao", com_locacao)
    leituras.registrar_contador(CLIENTE, "locacao_aberta", locacao_aberta)
    leituras.registrar_anotacao(FILIAL, "indicadores", anotar_filial, montar_filial)
    leituras.registrar_contador(FILIAL, "locacoes", locacoes_da_filial)
    leituras.registrar_contador(CATEGORIA, "locacoes_em_andamento", locacoes_da_categoria)
