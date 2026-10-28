from django.apps import AppConfig


class VeiculosConfig(AppConfig):
    name = "apps.veiculos"
    label = "veiculos"

    def ready(self) -> None:
        from apps.plataforma.services import registrar_conferencia_de_passo, registrar_contador
        from comum import leituras
        from comum.auditoria import registrar_formatador

        from . import eventos, selectors, textos  # noqa: F401 - eventos registra os assinantes

        registrar_formatador(
            ("categoria.definir_preco", "categoria.trocar_preco_agendado"), textos.tabela_de_preco
        )

        registrar_contador("veiculos", selectors.contar_veiculos_do_plano)  # PLT-03
        # IMP-07: o preço agendado marca o passo `precos` na leitura do andamento, na data.
        registrar_conferencia_de_passo("precos", selectors.tem_preco_vigente)
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
