from collections.abc import Callable

from django.apps import AppConfig

from comum.modulos import registrar_pendencia


def _comissoes_a_pagar() -> int:
    """PLT-12, FIN-09: comissões ainda não pagas nem estornadas."""
    from .models import Comissao, StatusComissao

    return Comissao.objects.exclude(
        status__in=[StatusComissao.PAGA, StatusComissao.ESTORNADA]
    ).count()


def _despesas(status: str) -> Callable[[], int]:
    """PLT-12: despesas abertas que seguram o downgrade (ADR 0024, item 7)."""

    def contar() -> int:
        from .models import Despesa

        return int(Despesa.objects.filter(status=status).count())

    return contar


class FinanceiroConfig(AppConfig):
    name = "apps.financeiro"
    label = "financeiro"

    def ready(self) -> None:
        from . import eventos, exportacao, leituras  # noqa: F401 - registra os assinantes

        leituras.registrar()
        registrar_pendencia("vendas_comissoes", "comissoes", _comissoes_a_pagar)  # PLT-12
        registrar_pendencia(
            "manutencao_despesas",
            "despesas_aguardando_aprovacao",
            _despesas("aguardando_aprovacao"),
        )
        registrar_pendencia("manutencao_despesas", "despesas_a_pagar", _despesas("a_pagar"))
        exportacao.registrar()  # item `despesas` da exportação (FIN-16, AUD-07)
