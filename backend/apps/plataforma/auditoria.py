"""O que a plataforma sabe sobre os eventos de auditoria (T-018, docs/api/auditoria.md).

- Para a auditoria da empresa: quem era o atendente de cada acesso de suporte (AUD-03), lido no
  `public` e registrado em `comum.auditoria` (o app `auditoria` fica abaixo deste).
- Para a auditoria da plataforma: em que empresa cada evento do `public` aconteceu, o filtro
  `?empresa=` e os indicadores da tela `Plat-Auditoria`.
"""

from datetime import timedelta
from typing import Any

from django.db.models import Q, QuerySet
from django_tenants.utils import get_public_schema_name, schema_context

from apps.auditoria.models import EventoAuditoria
from apps.auditoria.selectors import inicio_do_dia
from comum import auditoria, relogio
from comum.auditoria import Categoria

from .models import AcessoSuporte, Empresa

OBJETO_EMPRESA = "empresa"
OBJETO_ACESSO = "acessosuporte"


def acessos_suporte(ids: set[int]) -> dict[int, dict[str, Any]]:
    with schema_context(get_public_schema_name()):
        acessos = AcessoSuporte.objects.select_related("usuario").filter(pk__in=ids)
        return {
            a.pk: {
                "atendente": a.usuario.nome,
                "motivo": a.motivo,
                "permissao": a.permissao,
                "inicio": a.inicio,
            }
            for a in acessos
        }


def registrar() -> None:
    auditoria.registrar_consulta("acessos_suporte", acessos_suporte)


def de_empresa(qs: QuerySet[EventoAuditoria], empresa_id: int) -> QuerySet[EventoAuditoria]:
    """Eventos do `public` sobre a empresa: ela mesma e os acessos de suporte a ela."""
    acessos = AcessoSuporte.objects.filter(empresa_id=empresa_id).values_list("pk", flat=True)
    return qs.filter(
        Q(objeto_tipo=OBJETO_EMPRESA, objeto_id=empresa_id)
        | Q(objeto_tipo=OBJETO_ACESSO, objeto_id__in=list(acessos))
    )


def empresas_dos_eventos(eventos: list[EventoAuditoria]) -> dict[int, dict[str, Any] | None]:
    """`{id do evento: {id, nome_exibicao} ou None}`, com duas consultas para a página."""
    ids_acessos = {e.objeto_id for e in eventos if e.objeto_tipo == OBJETO_ACESSO and e.objeto_id}
    empresa_do_acesso = dict(
        AcessoSuporte.objects.filter(pk__in=ids_acessos).values_list("pk", "empresa_id")
    )
    ids_empresas = {
        e.objeto_id for e in eventos if e.objeto_tipo == OBJETO_EMPRESA and e.objeto_id
    } | set(empresa_do_acesso.values())
    nomes = dict(Empresa.objects.filter(pk__in=ids_empresas).values_list("pk", "nome_exibicao"))
    resultado: dict[int, dict[str, Any] | None] = {}
    for evento in eventos:
        empresa_id = None
        if evento.objeto_tipo == OBJETO_EMPRESA:
            empresa_id = evento.objeto_id
        elif evento.objeto_tipo == OBJETO_ACESSO and evento.objeto_id is not None:
            empresa_id = empresa_do_acesso.get(evento.objeto_id)
        resultado[evento.pk] = (
            {"id": empresa_id, "nome_exibicao": nomes[empresa_id]} if empresa_id in nomes else None
        )
    return resultado


def indicadores() -> dict[str, int]:
    agora = relogio.agora()
    entradas = EventoAuditoria.objects.filter(
        acao="suporte.entrar", ocorrido_em__gte=agora - timedelta(days=30)
    )
    hoje = inicio_do_dia(relogio.hoje())
    return {
        "acessos_suporte_30d": entradas.count(),
        "acessos_suporte_com_edicao_30d": entradas.filter(depois__permissao="ver_editar").count(),
        "logins_bloqueados_hoje": EventoAuditoria.objects.filter(
            acao="usuario.bloqueado", categoria=Categoria.SEGURANCA, ocorrido_em__gte=hoje
        ).count(),
        "mudancas_de_preco_7d": EventoAuditoria.objects.filter(
            acao__startswith="plano.", ocorrido_em__gte=agora - timedelta(days=7)
        ).count(),
    }
