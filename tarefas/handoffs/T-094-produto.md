# T-094 · Regra da ocupação com fração de dia · produto → orquestrador, arquiteto, qa

**O que foi feito:**
- **`VEI-06`:** conta o tempo exato entre as mudanças de status, com fração de dia. Um veículo alugado às 14:00 conta 0,42 daquele dia (10 h ÷ 24 h).
- **Registro:** nota de mudança de 09 out em Veículos e linha em "Decisões de 09 out 2026" (opção A, decidida pelo dono do produto).
- **`docs/api/veiculos.md`:** a seção `ocupacao` diz que conta a fração de dia (`VEI-06`), e não cita mais a `[decisão]`.
- **CA-013-29** em `docs/qa/criterios/T-013.md`. Com o relógio em 07 out às 00:00, um veículo na frota desde 27 set (10 dias) e alugado em 02 out às 14:00 fica com 4,4167 dias alugado e `ocupacao.pct = "44.17"`. Contando pelo dia, daria 40,00% ou 50,00%. Alugado em 02 out às 00:00, dá `"50.00"`.

**Onde:** `docs/regras-de-negocio.md` (`VEI-06`, nota de mudança, "Decisões de 09 out 2026"), `docs/api/veiculos.md` (`ocupacao`), `docs/qa/criterios/T-013.md` (CA-013-29), `tarefas/em-andamento.md`.

**Check:** só documentação; nenhum código ou teste mudou. Não rodei o `make backend-check`, porque a branch não muda nada do backend. O backlog fica com o PR #88.

**O que ficou de fora:** o teste `test_vei_06_*` do CA-013-29. O código da T-013 já calcula assim, e o teste confirma.

**Próximo passo para quem recebe:**
- **QA ou Backend:** acrescentar o caso do CA-013-29 ao teste da ocupação. O orquestrador decide quem.
