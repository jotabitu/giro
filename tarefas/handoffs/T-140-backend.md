# T-140 · Dias de atraso do bloqueio e km de saída da devolução · backend → orquestrador, qa, frontend

**O que foi feito:** branch `t-140-atraso-km`, a partir da `origin/main`.

- **D-03 (`CLI-05`):** `financeiro/leituras.py` registra o contador `dias_de_atraso` para `clientes.Cliente` (ADR 0015): dias de hoje da conta vencida mais antiga do cliente, sem a caução, por `relogio.hoje()` (dia corrido em `America/Sao_Paulo`). Em `clientes/selectors.py`, `_descricao_do_bloqueio` monta, no bloqueio automático, "Conta com N dias de atraso desde dd/mm/aaaa" com esse número (a data é hoje menos N, o vencimento da conta). Bloqueio manual, ou sem conta vencida, usa a descrição gravada. O serviço continua gravando a descrição do dia no cliente e no `motivo` do evento `cliente.bloquear`, que não muda.
- **D-12 (`DEV-08`):** `vistorias.services.km_de_saida` dá o km de saída da devolução: o `km_saida` da locação quando a chegada é do veículo atual da locação (o mesmo número da ficha); senão, o da vistoria de saída. Usado no `comparacao` de `GET /api/devolucoes/{id}/` e no recibo em PDF. Na troca pendente a locação ainda tem o veículo antigo e o km dele; depois da conclusão, o km da locação é o do novo.
- O combustível de saída continua vindo da vistoria de saída: a locação não grava combustível. Como o seed já cria a vistoria de saída da LOC-2836 (T-138), os dois batem; não abri `[decisão]` nem campo novo.
- Contratos: nota em `docs/api/clientes.md` (`bloqueio.descricao`) e em `docs/api/vistorias.md` (`comparacao.km.saida`). Forma das respostas igual, OpenAPI sem mudança.

**Testes** (`tests/aceitacao/test_t019_seed_completo.py`, sobre o seed):
- `test_cli_05_dias_de_atraso_de_hoje`: Rafael em 07 out "Conta com 25 dias de atraso desde 12/09/2026", em 12 out "Conta com 30 dias..."; o evento continua com 25.
- `test_dev_08_km_de_saida_igual_na_ficha_e_na_devolucao`: LOC-2836 com 21.870 na ficha e na devolução, também com a vistoria de saída tirada de vigência (o caso do seed antigo).
- `test_dev_08_km_de_saida_na_troca_e_o_do_veiculo_que_volta`: na troca, o Factor volta com 21.870; depois, ficha e devolução final com o km do NMax.
- `test_t016_vistorias.py::_saida_direta` passou a gravar o km também na locação (como `registrar_vistoria_saida`): a carteira deixava 21.870 na locação e 18.402 na vistoria, estado que a `DEV-08` não admite.

ruff, ruff format, mypy e pytest verdes (suíte em série; com `-n auto` o Postgres de teste do worktree estoura a memória compartilhada, sem relação com a tarefa).

**Para o QA:** a T-138 já tinha resolvido o D-12 pelo seed; o comparativo agora não depende mais da vistoria de saída para o km. Pode tirar qualquer anotação de defeito conhecido do D-03 e do D-12 no E2E.

**Para o frontend:** nada muda; a ficha e a devolução só exibem o que a API devolve.

**Próximo passo:** orquestrador abre o PR. Sigo para a T-146.
