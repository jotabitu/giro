# T-310 · Baixa de veículo com movimentação aberta · produto → orquestrador, arquiteto, backend (T-288), frontend, qa

Decisão do dono em 16 out 2026: **opção B**, recomendada pelo produto na T-302 (ponto do arquiteto na T-300).

**O que foi feito:**

- **`MOV-03`:** a baixa do veículo (só o administrador, com motivo) encerra a movimentação aberta:
  - a `agendada` vira `cancelada`;
  - a iniciada (`em_transito` ou `no_local`) vira `cancelada` com o motivo "Veículo baixado: {motivo da baixa}";
  - as despesas das paradas já lançadas (`MOV-04`) ficam como estão;
  - na transferência, a `MOV-06` não acontece, e o veículo continua na filial de saída;
  - a baixa e o cancelamento ficam na auditoria.
- **Transições da movimentação:** é a única exceção a "depois de iniciada, não se cancela".
- **Tabela de transições do veículo:** a linha "qualquer, exceto `alugado`" → `baixado` aponta para a `MOV-03`.
- **Registro:**
  - linha na tabela "Decisões de 16 out 2026";
  - nota de mudança na seção Movimentações;
  - o item saiu de "Pontos em aberto";
  - a `[decisão]` do backlog está riscada, com a resposta.
- **Critérios em `docs/qa/criterios/T-246.md`:**
  - CA-246-22: a MOV-0001 do SAK-1D39 com a despesa de R$ 35,00, baixa por "roubo" no caminho;
  - CA-246-23: transferência Centro → Caucaia sem `TransferenciaVeiculo`; a agendada do PMZ-3E17 cancelada; o gerente recebe 403.

**Onde:** `docs/regras-de-negocio.md`, `docs/qa/criterios/T-246.md`, `tarefas/backlog.md`, `tarefas/feito.md`.
**Regras cobertas:** MOV-03, MOV-04, MOV-06, transições do veículo.

**Próximo passo:**
- **Arquiteto:** em `docs/api/veiculos.md` e `movimentacoes.md`, a baixa com movimentação aberta deixa de ser recusada (sai a sugestão do 409 `MOV-03` da T-300). Também:
  - o cancelamento da iniciada vem da baixa, sem rota nova;
  - `motivo_cancelamento` com "Veículo baixado: {motivo}";
  - o evento de auditoria do cancelamento.
- **Backend (T-288):** a baixa cancela a movimentação na mesma transação. A recusa provisória (A) deixa de valer. Testes `test_mov_03_baixa_cancela_movimentacao_iniciada`, `test_mov_03_baixa_na_transferencia_nao_transfere` e `test_mov_03_baixa_cancela_agendada`.
- **Frontend:** o diálogo de baixa do veículo em movimentação pode avisar "A MOV-0001 será cancelada." O texto vem da API, se o contrato trouxer.
- **QA:** CA-246-22 e 23.
- **Orquestrador:** abrir o PR desta branch.
