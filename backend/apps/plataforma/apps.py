from django.apps import AppConfig


class PlataformaConfig(AppConfig):
    name = "apps.plataforma"
    label = "plataforma"

    def ready(self) -> None:
        # O token de suporte é conferido no `public` a cada requisição (ADR 0013, item 2).
        from comum.autenticacao import registrar_suporte
        from comum.empresa import registrar_recursos

        from . import auditoria
        from .selectors import recursos_ligados, recusa_do_modulo
        from .services import conferir_acesso_suporte

        registrar_suporte(conferir_acesso_suporte)
        registrar_recursos(recursos_ligados, recusa_do_modulo)  # PLT-12 (ADR 0024, item 2)
        auditoria.registrar()  # atendente de cada acesso na auditoria da empresa (AUD-03)
