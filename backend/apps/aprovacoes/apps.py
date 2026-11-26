from django.apps import AppConfig


class AprovacoesConfig(AppConfig):
    name = "apps.aprovacoes"
    label = "aprovacoes"

    def ready(self) -> None:
        from comum import aprovacoes, leituras

        from . import selectors, services
        from .models import OrigemPedido, PedidoAprovacao

        def historico_do_cliente(cliente_id: int) -> int:
            """CLI-13: pedido de aprovação do cliente (desbloqueio, APR-05), em qualquer estado."""
            pedidos = PedidoAprovacao.objects.filter(
                origem_tipo=OrigemPedido.CLIENTE, origem_id=cliente_id
            )
            return int(pedidos.exists())

        leituras.registrar_contador("clientes.Cliente", "historico_aprovacao", historico_do_cliente)

        # Os outros apps abrem pedidos só pela porta em `comum` (ADR 0019).
        aprovacoes.registrar(
            pedir=services.pedir,
            pendente=selectors.pendente,
            cancelar_pendentes=services.cancelar_pendentes,
        )
