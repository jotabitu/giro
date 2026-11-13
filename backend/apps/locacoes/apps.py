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
        from comum.auditoria import registrar_formatador

        from . import contrato, eventos, leituras, textos  # noqa: F401 - eventos assina

        leituras.registrar()
        contrato.registrar()
        from apps.financeiro.services import registrar_trava_da_conta

        from .services import travar_caucao_da_compra

        registrar_trava_da_conta(travar_caucao_da_compra)  # LOC-16: a caução da compra
        registrar_pendencia("locacoes_vistoria", "locacoes", _locacoes_abertas)  # PLT-12
        # Textos da auditoria da compra (LOC-16, T-420)
        registrar_formatador("locacao.quitar", textos.quitar)
        registrar_formatador("locacao.encerrar_por_atraso", textos.encerrar_por_atraso)
        registrar_formatador(tuple(textos.RESUMOS_DO_PLANO), textos.plano_de_compra)
