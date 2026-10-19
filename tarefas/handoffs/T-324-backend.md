# T-324 · Suporte nas escritas do financeiro · backend → qa, segurança, orquestrador

**O que foi feito:** opção A do dono. As quatro rotas que davam 500 com o suporte em "ver e editar" (a view gravava o `AtorSuporte` num campo `contas.Usuario`) passaram a dar 403 `PLT-07`: `POST caixas/`, `POST caixas/{id}/fechar/`, `POST despesas/` e `POST reembolsos/{id}/feito/`. Foi feito por `suporte_proibido` nas views (`frozenset({"POST"})` em `DespesasView`, que também lista), como na T-316: a conferência roda na autenticação, antes de ler o arquivo e de validar o corpo.
**Onde:** `backend/apps/financeiro/api/views.py`, `docs/api/financeiro.md` ("Quem pode").
**Contrato:** sem rota nova; OpenAPI sem mudança.
**Regras cobertas:** PLT-07, FIN-05, FIN-07: `test_plt_07_fin_05_fin_07_suporte_nao_escreve_no_financeiro` (as quatro, com arquivo inválido e campo inválido, dão 403 `PLT-07`). `QUEBRADAS` de `test_t317_varredura_suporte.py` ficou vazia, e a varredura passa nas quatro. t317 e t017: 181 passam; ruff e mypy limpos.
**O que ficou de fora:** as outras escritas do financeiro (receber, sangria, pagar despesa etc.) seguem como estavam, porque a varredura não acusou 500 nelas.
**Próximo passo para quem recebe:** qa e segurança: conferir; orquestrador: abrir o PR.
