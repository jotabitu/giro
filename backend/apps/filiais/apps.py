from django.apps import AppConfig


class FiliaisConfig(AppConfig):
    name = "apps.filiais"
    label = "filiais"

    def ready(self) -> None:
        from apps.plataforma.services import registrar_contador
        from comum import leituras
        from comum.auditoria import registrar_consulta
        from comum.permissoes import registrar_escopo_de_filial, registrar_resumo_de_filiais

        from . import eventos, selectors

        registrar_escopo_de_filial(selectors.filiais_do_usuario)  # USR-07
        registrar_resumo_de_filiais(selectors.resumo_das_filiais)
        registrar_consulta("filiais", selectors.nomes_das_filiais)  # auditoria (T-018)
        registrar_contador("filiais", eventos.contar_filiais_ativas)  # PLT-03
        leituras.registrar_anotacao(
            selectors.ALVO, "indicadores", selectors.anotar_usuarios, selectors.montar_usuarios
        )
