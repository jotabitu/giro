from django.urls import path

from . import views

urlpatterns = [
    path("financeiro/contas-receber/", views.ContasReceberView.as_view()),
    path("financeiro/contas-receber/renegociar/", views.RenegociarView.as_view()),
    path("financeiro/contas-receber/cobrar-em-lote/", views.CobrarEmLoteView.as_view()),
    path("financeiro/contas-receber/<int:pk>/", views.ContaReceberView.as_view()),
    path("financeiro/contas-receber/<int:pk>/receber/", views.ReceberView.as_view()),
    path("financeiro/contas-receber/<int:pk>/cobranca/", views.CobrancaView.as_view()),
    path("financeiro/contas-receber/<int:pk>/cobrar/", views.CobrarView.as_view()),
    path("financeiro/contas-receber/<int:pk>/cancelar/", views.CancelarContaView.as_view()),
    path("financeiro/contas-receber/<int:pk>/estornar/", views.EstornarContaView.as_view()),
    path("financeiro/reembolsos/", views.ReembolsosView.as_view()),
    path("financeiro/reembolsos/<int:pk>/feito/", views.ReembolsoFeitoView.as_view()),
    path("financeiro/pendencias-pagamento/", views.PendenciasView.as_view()),
    path(
        "financeiro/pendencias-pagamento/<int:pk>/resolver/",
        views.ResolverPendenciaView.as_view(),
    ),
    path("financeiro/caixas/", views.CaixasView.as_view()),
    path("financeiro/caixas/hoje/", views.CaixaHojeView.as_view()),
    path("financeiro/caixas/<int:pk>/", views.CaixaView.as_view()),
    path("financeiro/caixas/<int:pk>/movimentos/", views.MovimentosView.as_view()),
    path(
        "financeiro/caixas/<int:pk>/movimentos/<int:mid>/estornar/",
        views.EstornarMovimentoView.as_view(),
    ),
    path("financeiro/caixas/<int:pk>/sangria/", views.SangriaView.as_view()),
    path("financeiro/caixas/<int:pk>/fechar/", views.FecharCaixaView.as_view()),
    path("financeiro/despesas/", views.DespesasView.as_view()),
    path("financeiro/despesas/<int:pk>/", views.DespesaView.as_view()),
    path("financeiro/despesas/<int:pk>/pagar/", views.PagarDespesaView.as_view()),
]

# Host da plataforma (schema public, `config/urls_publico.py`): o aviso do parceiro (S-14).
urls_webhooks = [
    path("webhooks/pagamentos/asaas/", views.WebhookAsaasView.as_view()),
]
