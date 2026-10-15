# T-162 · Flag `lancamento_avulso` em `pode` (parte do backend) · backend → orquestrador, frontend, produto

**O que foi feito:** branch `t-162-lancamento-avulso`, a partir da `origin/main`.

- **Decisão:** a tabela de perfis das regras não dizia quem faz o lançamento avulso; abri `[decisão]` no backlog e o produto respondeu em 15 out 2026: administrador, gerente (sua filial) e financeiro sim; vendedor e vistoriador não; a permissão extra `cancelar_contrato` (`USR-03`) não entra. É a linha de "Quem pode" de `docs/api/financeiro.md`, que a API já aplicava (`GERENCIAM` no `POST /api/financeiro/contas-receber/`). A linha entrou na tabela de perfis pela T-232 (branch `t-232-perfil-lancamento-avulso`, PR a abrir): "Lançamento avulso em contas a receber (multa, avaria, outro), cancelar, renegociar, estornar" = administrador, gerente e financeiro.
- `contas/selectors.py`: `TABELA_DO_PODE["lancamento_avulso"] = _so(ADM, GER, FIN)`; `PodeDaEmpresaSerializer` com o campo `lancamento_avulso` (bool).
- `docs/api/contas.md`: linha nova na tabela do `pode` e nota ligando a chave à linha de `financeiro.md`. `docs/api/openapi.yaml` regenerado (só o campo novo).

**Regras cobertas:** tabela de perfis (linha da T-232), FIN-07.

**Testes:** `tests/aceitacao/test_t017_financeiro.py::test_fin_07_lancamento_avulso_por_perfil`: Mariana, Rodrigo e Lúcia `true`; Bruna e João `false`; Bruna e João recebem 403 no `POST` do lançamento. ruff, ruff format, mypy e pytest verdes.

**Para o frontend:** rode `api:gerar` e troque a condição do botão "Novo lançamento" (`despesas_aprovar || financeiro_pagar`) por `pode.lancamento_avulso`. O resultado por perfil é o mesmo de hoje.

**Para o orquestrador:** o PR da T-232 (regras) e este podem entrar em qualquer ordem; o código não muda.

**Próximo passo:** orquestrador abre o PR; a tarefa segue no backlog para o frontend.
