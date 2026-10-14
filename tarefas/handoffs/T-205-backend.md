# T-205 · Caução na busca do caixa (D-01 da T-025) · backend → orquestrador, qa, frontend

**O que foi feito:** branch `t-205-caucao-busca-caixa`, a partir da `origin/main`.

- `financeiro/selectors.py::_recortar` agora trata `?busca=` como recorte, igual a `?cliente=` e `?origem_tipo=&origem_id=`. Com busca, a lista de `GET /api/financeiro/contas-receber/` traz a caução (`tipo = caucao`), que era o que `docs/api/financeiro.md` já dizia ("Com `?cliente=`, `?origem_tipo=&origem_id=` ou `?busca=` (...) a lista continua trazendo a caução"). Sem contrato novo e sem OpenAPI novo: a forma da resposta não mudou.
- As contagens e os indicadores continuam sem a caução (`FIN-15`): a base deles já a exclui.
- O recebimento da caução no caixa (`POST /api/financeiro/contas-receber/{id}/receber/`) já aceitava a caução; o que faltava era a tela achá-la.

**Regras cobertas:** FIN-15 (CA-023-15, última linha: "A caução do cliente aparece para receber quando a busca é por cliente ou por locação").

**Testes:** `tests/aceitacao/test_t148_decisoes_t017.py::test_fin_15_busca_do_caixa_traz_caucao`: Lucas, LOC-2856, caução de R$ 300,00; busca "LOC-2856" e "Lucas" trazem a caução, `contagens.todas` não a conta, a lista geral não a traz, e a Bruna abre o caixa e recebe a caução em dinheiro (conta `paga`). `make backend-check` (ruff, mypy, pytest) verde.

**Observação:** qualquer busca não vazia traz as cauções que casarem com o termo (por nome do cliente ou código da origem), também na tela `Receber`, que usa a mesma rota. É a leitura literal do contrato; se o produto quiser a caução só no caixa, vira `[decisão]`.

**Para o QA:** troque o contorno do E2E (caução recebida pelo serviço) pela tela do caixa e tire o `defeitoConhecido` do D-01.

**Próximo passo:** orquestrador abre o PR. Sigo para a T-207.
