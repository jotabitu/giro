from django.apps import AppConfig


class VeiculosConfig(AppConfig):
    name = "apps.veiculos"
    label = "veiculos"

    def ready(self) -> None:
        from apps.plataforma.services import registrar_contador
        from comum import leituras

        from . import selectors

        registrar_contador("veiculos", selectors.contar_veiculos_do_plano)  # PLT-03
        # Operação que impede desativar a filial (FIL-06) e indicadores da lista de filiais.
        leituras.registrar_contador(
            selectors.ALVO_FILIAL, "veiculos", selectors.veiculos_em_operacao
        )
        leituras.registrar_anotacao(
            selectors.ALVO_FILIAL,
            "indicadores",
            selectors.anotar_indicadores,
            selectors.montar_indicadores,
        )
