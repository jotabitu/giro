from django.apps import AppConfig

from comum.modulos import registrar_pendencia


def _locacoes_abertas() -> int:
    """PLT-12: o que impede deixar de alugar (troca do ramo, `empresas.md`)."""
    from .models import Locacao, StatusLocacao

    return Locacao.objects.filter(
        status__in=[
            StatusLocacao.AGUARDANDO_RETIRADA,
            StatusLocacao.ATIVA,
            StatusLocacao.DEVOLUCAO_ATRASADA,
        ]
    ).count()


class LocacoesConfig(AppConfig):
    name = "apps.locacoes"
    label = "locacoes"

    def ready(self) -> None:
        from . import contrato, eventos, leituras  # noqa: F401 - eventos registra os assinantes

        leituras.registrar()
        contrato.registrar()
        registrar_pendencia("locacoes_vistoria", "locacoes", _locacoes_abertas)  # PLT-12
