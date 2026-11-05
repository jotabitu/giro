"""`/api/publico/compra/`: só no domínio principal, pelo `urls_publico` (`compra.md`)."""

from django.urls import path

from .compra import (
    CatalogoView,
    CnpjView,
    ConfirmarView,
    PedidosView,
    PedidoView,
    ReenviarView,
    SubdominioView,
)

urls_compra = [
    path("planos/", CatalogoView.as_view(), name="compra-planos"),
    path("cnpj/", CnpjView.as_view(), name="compra-cnpj"),
    path("subdominio/", SubdominioView.as_view(), name="compra-subdominio"),
    path("pedidos/", PedidosView.as_view(), name="compra-pedidos"),
    path("pedidos/<str:chave>/", PedidoView.as_view(), name="compra-pedido"),
    path("pedidos/<str:chave>/confirmar/", ConfirmarView.as_view(), name="compra-confirmar"),
    path("pedidos/<str:chave>/reenviar-codigo/", ReenviarView.as_view(), name="compra-reenviar"),
]
