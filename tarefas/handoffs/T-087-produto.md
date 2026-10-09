# T-087 · Regras da CNH C, D e E e do cliente bloqueado · produto → orquestrador, qa, backend

**O que foi feito:**
- **`CLI-02`:** C, D e E alugam carro, porque incluem a B (CTB, art. 143), mas não alugam moto. AB, AC, AD e AE alugam moto e carro.
- **`CLI-09`:** cliente `bloqueado` não pode ser inativado (409 `transicao_cliente`). Primeiro ele é desbloqueado (`CLI-05`).
- **Registro:** nota de mudança de 09 out em Clientes e seção nova "Decisões de 09 out 2026", com as duas linhas.
- **Critérios em `docs/qa/criterios/T-014.md`** (não existiam):
  - **CA-014-14:** CNH C, D ou E aluga carro, mas para moto dá `CLI-02`; AB a AE alugam moto e carro.
  - **CA-014-18:** inativar Rafael (`bloqueado`) dá 409 `transicao_cliente`, e ele continua bloqueado. Um bloqueado à mão, sem pendências, depois de desbloqueado, é inativado.

**Onde:** `docs/regras-de-negocio.md` (`CLI-02`, `CLI-09`, nota de mudança, "Decisões de 09 out 2026"), `docs/qa/criterios/T-014.md` (CA-014-14 e CA-014-18), `tarefas/em-andamento.md`.

**Check:** só documentação; nenhum código ou teste mudou. Não rodei o `make backend-check`, porque a branch não muda nada do backend.

**O que ficou de fora:** o código da T-014 já segue as duas regras (`backend/apps/clientes/selectors.py` tem as categorias). Os testes `test_cli_02_ca_014_14_*` e `test_cli_09_ca_014_18_*` ainda não cobrem os casos novos.

**Próximo passo para quem recebe:**
- **QA ou Backend:** acrescentar os casos novos aos dois testes. O orquestrador decide quem e quando.
- **Orquestrador:** a linha `[decisão]` da T-014 no backlog fica com o PR #82.
