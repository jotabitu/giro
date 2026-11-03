# T-416 · Ver o comprovante da despesa paga · backend → frontend, qa

**O que foi feito:** a representação da despesa ganhou `comprovante`, o arquivo enviado no pagamento (`POST /api/financeiro/despesas/{id}/pagar/`), com URL assinada de 15 minutos (`AUD-05`), nova a cada leitura, no mesmo formato da `nota` (`{ "url", "url_expira_em" }`). Vem na lista, no detalhe, no lançamento, no anexar nota e na resposta do pagamento. É `null` quando a despesa não foi paga, quando foi paga sem comprovante e, sempre, para o token de suporte (`AUD-09`), como o comprovante do reembolso (M-02 da T-384).

**Onde:** `backend/apps/financeiro/selectors.py` (`representacao_despesa(despesa, *, suporte)`), `backend/apps/financeiro/api/serializers.py` (`DespesaSerializer.comprovante`), `backend/apps/financeiro/api/views.py` (as cinco rotas passam `suporte`).

**Contrato:** `docs/api/financeiro.md`, "Despesas · Representação" e "POST /api/financeiro/despesas/{id}/pagar/"; `docs/api/openapi.yaml` (`Despesa.comprovante`, obrigatório e anulável). Sem migração: o campo `Despesa.comprovante` já existia.

**Regras cobertas:** `FIN-05`, `AUD-05`, `AUD-09` (testes em `backend/tests/aceitacao/test_t416_comprovante_despesa.py`: `test_fin_05_aud_05_comprovante_da_despesa_paga`, `test_fin_05_despesa_paga_sem_comprovante`, `test_aud_09_suporte_nao_recebe_o_comprovante_da_despesa`).

**Ponto para a segurança e o produto:** esconder o comprovante do suporte segue o precedente do reembolso; a nota da despesa continua visível para o suporte, como antes. Se o produto preferir o comprovante visível ao suporte (é pagamento a fornecedor, não documento do cliente), basta tirar o `suporte` da chamada.

**O que ficou de fora:** a tela. O frontend faz o botão "Ver comprovante" na despesa paga.

**Próximo passo para quem recebe:**
- frontend: rode `npm run api:gerar`; no detalhe da despesa paga, mostre "Ver comprovante" quando `comprovante` vier preenchido, abrindo `comprovante.url` como já faz com a nota. A URL vence em 15 minutos: peça o detalhe de novo para abrir outra vez.
- qa: o cenário é o óleo de R$ 48,00 lançado pela Bruna em 07 out e pago pela Lúcia por Pix com o comprovante.
