# T-308 · Marco da régua da assinatura perdido · produto → orquestrador, backend (T-303), qa (T-204, T-215)

Decisão do dono em 16 out 2026: **opção B**, recomendada pelo produto na T-299.

**O que foi feito:**

- `PLT-02`: cada marco sai uma vez, no dia dele. Se a tarefa da régua não rodar nesse dia, o D-3, o D0 e o D+3 não saem depois. O D+7 (aviso de suspensão e tarefa de ligação) sai na próxima execução até o D+14, uma vez só. Ele não sai depois do D+14, nem com a fatura paga ou cancelada, nem com a empresa `cancelada`.
- `AUT-13`: a linha da tabela de automações aponta para isso.
- Linha nova na tabela "Decisões de 16 out 2026", nota de mudança na seção Plataforma, e o item saiu de "Pontos em aberto".
- Critério CA-ASS-68 em `docs/qa/criterios/assinatura.md`, com a Moto Rápida: FAT-0001 vence em 22 out; a tarefa não roda em 25 e 29 out e volta em 30 out; o D+7 sai em 30 out com a ligação, e o D+3 não sai; nada em 31 out; a tarefa voltando só em 06 nov (depois do D+14, 05 nov), o D+7 não sai; paga ou `cancelada`, nada.
- Backlog: a `[decisão]` riscada, com a resposta.

**Onde:** `docs/regras-de-negocio.md`, `docs/qa/criterios/assinatura.md`, `tarefas/backlog.md`, `tarefas/feito.md`.
**Regras cobertas:** PLT-02, AUT-13.

**Próximo passo:**
- **Backend (T-303):** já conta com B; teste `test_aut_13_d7_perdido_sai_ate_d14` pelo CA-ASS-68. A marca "já avisada" continua sendo o evento `fatura_assinatura.regua` com `marco: "D+7"`, e a busca do dia precisa incluir as faturas com vencimento entre D+8 e D+14 que ainda não têm esse evento.
- **QA:** CA-ASS-68 com o relógio de referência.
- **Orquestrador:** abrir o PR desta branch.
