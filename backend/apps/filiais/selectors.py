"""Leituras das filiais: escopo da pessoa (USR-07), horário e feriados (LOC-11, FIL-03).

Interface para os outros apps (contrato de filiais): `filiais_do_usuario`, `filtrar_por_filial`,
`esta_aberta` e `proxima_abertura`. Os módulos filtram por filial só com `filtrar_por_filial`;
ninguém lê `filial_da_requisicao` e filtra por conta própria (F-02 da T-064).
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.db.models import Count, Q, QuerySet

from comum import leituras, relogio
from comum.erros import SemPermissao
from comum.permissoes import TODAS_AS_FILIAIS, filial_pedida, pode_escolher_todas

from .calendario import aberta_em, proxima_abertura_em, resumo_do_horario
from .models import FeriadoFilial, Filial, UsuarioFilial

ALVO = "filiais.Filial"
INDICADORES_VAZIOS: dict[str, Any] = {
    "veiculos": None,
    "locacoes_ativas": None,
    "usuarios": None,
    "ocupacao_pct": None,
}
MES_DO_AVISO_DO_ANO_SEGUINTE = 11  # a partir de 1º de novembro


# --- Escopo (USR-07) ---


def filiais_do_usuario(usuario: Any) -> set[int]:
    """Ids das filiais ativas da pessoa; todas as ativas para o administrador."""
    if pode_escolher_todas(usuario):
        return set(Filial.ativos.values_list("pk", flat=True))
    return set(
        UsuarioFilial.objects.filter(usuario=usuario, filial__ativo=True).values_list(
            "filial_id", flat=True
        )
    )


def minhas_filiais(usuario: Any) -> QuerySet[Filial]:
    return Filial.ativos.filter(pk__in=filiais_do_usuario(usuario)).order_by("-matriz", "nome")


@dataclass(frozen=True)
class TodasAsFiliais:
    """`X-Filial: todas`. `ids` são todas as filiais da empresa, inclusive as desativadas, que
    ainda têm contas e histórico (USR-07, FIL-06). Nunca `None`, para não se confundir com
    "pessoa sem filial"."""

    ids: frozenset[int]


def sem_filial_nenhuma() -> SemPermissao:
    return SemPermissao("USR-07", "Você não tem acesso a nenhuma filial")


def filial_da_requisicao(request: Any) -> Filial | TodasAsFiliais:
    """Filial do `X-Filial` (só ativa do escopo, conferida em `filial_pedida`) ou
    `TodasAsFiliais`. Sem cabeçalho: a matriz, se a pessoa tem acesso a ela, ou a primeira
    filial da pessoa. Pessoa sem filial ativa: 403 `USR-07`."""
    pedida = filial_pedida(request)
    if pedida == TODAS_AS_FILIAIS:
        return TodasAsFiliais(frozenset(Filial.objects.values_list("pk", flat=True)))
    if isinstance(pedida, int):
        return Filial.objects.get(pk=pedida)
    filial = minhas_filiais(request.user).first()
    if filial is None:
        raise sem_filial_nenhuma()
    return filial


def filtrar_por_filial(queryset: QuerySet[Any], request: Any, campo: str = "filial") -> Any:
    """O único jeito de os módulos filtrarem pelo escopo de filial da requisição (USR-07)."""
    escopo = filial_da_requisicao(request)
    if isinstance(escopo, TodasAsFiliais):
        return queryset.filter(**{f"{campo}__in": escopo.ids})
    return queryset.filter(**{campo: escopo.pk})


# --- Horário e feriados (FIL-03, LOC-11) ---


def _no_fuso(filial: Filial, momento: datetime) -> datetime:
    return momento.astimezone(ZoneInfo(filial.fuso))


def _feriados(filial: Filial, de: date) -> set[date]:
    return set(filial.feriados.filter(ativo=True, data__gte=de).values_list("data", flat=True))


def esta_aberta(filial: Filial, momento: datetime) -> bool:
    local = _no_fuso(filial, momento)
    return aberta_em(filial.horario, _feriados(filial, local.date()), local)


def proxima_abertura(filial: Filial, momento: datetime) -> datetime | None:
    """O próprio momento, se aberta; senão a próxima abertura, pulando dias fechados e feriados."""
    local = _no_fuso(filial, momento)
    return proxima_abertura_em(filial.horario, _feriados(filial, local.date()), local)


def feriados_proximos(filial: Filial, quantos: int = 3) -> list[dict[str, Any]]:
    return [
        {"data": f.data, "nome": f.nome}
        for f in filial.feriados.filter(ativo=True, data__gte=relogio.hoje())[:quantos]
    ]


def feriados_ano_seguinte_pendentes(filial: Filial) -> bool:
    hoje = relogio.hoje()
    if hoje.month < MES_DO_AVISO_DO_ANO_SEGUINTE:
        return False
    return not filial.feriados.filter(ativo=True, data__year=hoje.year + 1).exists()


def feriados_do_ano(filial: Filial, ano: int) -> QuerySet[FeriadoFilial]:
    return filial.feriados.filter(ativo=True, data__year=ano)


# --- Representação ---


def gerentes(filial: Filial) -> list[dict[str, Any]]:
    return [
        {"id": pk, "nome": nome}
        for pk, nome in get_user_model()
        .objects.filter(perfil="gerente", status="ativo", filiais_ligadas__filial=filial)
        .order_by("nome")
        .values_list("pk", "nome")
    ]


def endereco_resumo(filial: Filial) -> str:
    return f"{filial.logradouro}, {filial.numero} · {filial.cidade}, {filial.uf}"


def representacao(filial: Filial) -> dict[str, Any]:
    return {
        "id": filial.pk,
        "nome": filial.nome,
        "matriz": filial.matriz,
        "ativo": filial.ativo,
        "cnpj": filial.cnpj or None,
        "inscricao_estadual": filial.inscricao_estadual or None,
        "inscricao_municipal": filial.inscricao_municipal or None,
        "endereco": {
            "cep": filial.cep,
            "logradouro": filial.logradouro,
            "numero": filial.numero,
            "complemento": filial.complemento or None,
            "bairro": filial.bairro,
            "cidade": filial.cidade,
            "uf": filial.uf,
        },
        "contato": {
            "telefone": filial.telefone,
            "whatsapp": filial.whatsapp,
            "email": filial.email,
        },
        "preco_litro_centavos": filial.preco_litro_centavos,
        "horario": filial.horario,
        "horario_resumo": resumo_do_horario(filial.horario),
        "endereco_resumo": endereco_resumo(filial),
        "gerentes": gerentes(filial),
        "feriados_proximos": feriados_proximos(filial),
        "feriados_ano_seguinte_pendentes": feriados_ano_seguinte_pendentes(filial),
        "criado_em": filial.criado_em,
    }


def item_da_lista(filial: Filial) -> dict[str, Any]:
    indicadores = {**INDICADORES_VAZIOS, **leituras.blocos(ALVO, filial).get("indicadores", {})}
    return {**representacao(filial), "indicadores": indicadores}


def lista(ativo: str | None = None, busca: str | None = None) -> QuerySet[Filial]:
    qs = leituras.aplicar(ALVO, Filial.objects.all())
    if ativo in ("true", "false"):
        qs = qs.filter(ativo=ativo == "true")
    if busca and busca.strip():
        qs = qs.filter(Q(nome__icontains=busca.strip()) | Q(cidade__icontains=busca.strip()))
    return qs


# Indicador `usuarios` do bloco `indicadores`, fornecido pelo próprio app (contrato de filiais).
def anotar_usuarios(queryset: QuerySet[Any]) -> QuerySet[Any]:
    return queryset.annotate(  # type: ignore[no-any-return]
        _indicador_usuarios=Count(
            "usuarios_ligados",
            filter=Q(usuarios_ligados__usuario__status__in=["ativo", "convite_pendente"]),
            distinct=True,
        )
    )


def montar_usuarios(filial: Any) -> dict[str, Any] | None:
    valor = getattr(filial, "_indicador_usuarios", None)
    return None if valor is None else {"usuarios": valor}
