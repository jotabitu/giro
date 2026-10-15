# T-150 · Filial nos eventos de movimento de caixa · backend → orquestrador, qa

**O que foi feito:** branch `t-150-filial-movimento-caixa`, a partir da `origin/main`. Decisão do arquiteto de 12 out mantida: a ação continua `movimento_caixa.<verbo>`, objeto `movimentocaixa`.

- `comum/auditoria.py`: `registrar_evento` e `auditar` aceitam `filial_id: int | None = None` (keyword). Quando vem, vale ele; senão, `getattr(objeto, "filial_id", None)`, como antes. Sem mudança de schema.
- `financeiro/services.py`: `_registrar_movimento` (entrada, saída, sangria e estorno) e o `registrar_evento("movimento_caixa.estorno_motivo", ...)` de `estornar_movimento` passam `filial_id=caixa.filial_id`.
- `auditoria/textos.py`: o detalhe da `movimento_caixa.sangria` é "Caixa da <filial>" (consulta `filiais`, a mesma do `objeto.filial`; o selector agora põe os nomes no apoio, sem consulta a mais). Sem filial, cai na descrição. Sai a entrada `caixa.sangria`, que nenhum serviço grava.
- Sem migração de dados (eventos imutáveis, ADR 0010; o seed é recriado). Contrato em `docs/api/auditoria.md` já ajustado na T-151; OpenAPI sem mudança.

**Regras cobertas:** FIN-07, AUD-01, AUD-02.

**Testes:**
- `test_t019_seed_completo.py::test_fin_07_sangria_audita_com_filial_do_caixa` (era o `xfail` `test_fin_07_seed_019_25_sangria_com_a_filial`): seed em 07 out, filtro pela Filial Centro traz a sangria da Bruna com `resumo` "Fez sangria de R$ 500,00", `detalhe` "Caixa da Filial Centro" e `objeto.filial` "Filial Centro".
- `test_t017_financeiro.py::test_fin_07_movimentos_e_estorno_auditam_com_filial`: entrada, saída, sangria, estorno e `estorno_motivo` com o `filial_id` do caixa; filtro pela Caucaia não traz nenhum.
- `test_t018_auditoria.py`: o evento de apoio montado à mão passou de `caixa.sangria` (objeto `caixa`) para `movimento_caixa.sangria` (objeto `movimentocaixa`), a ação que o serviço grava; o filtro por objeto separa o caixa (abertura) do movimento (sangria). Os testes de auditoria de objetos com `filial_id` próprio passam sem mudança.
- ruff, ruff format, mypy e pytest verdes.

**Para o QA:** o CA-019-25 da sangria deixou de ser `xfail`.

**Próximo passo:** orquestrador abre o PR. Sigo para a T-162.
