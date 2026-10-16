# T-319 · Suporte Giro só lê as movimentações · produto → orquestrador, backend (T-316), segurança, qa

Decisão do dono em 16 out 2026: **opção A**, recomendada pelo produto e pela segurança na T-318 (pergunta da T-315).

**O que foi feito:**

- **Regra:** a `MOV-02` e a `PLT-07` dizem que o suporte Giro, mesmo em "ver e editar", só lê as movimentações. Recebem 403 `PLT-07`:
  - criar, editar a agendada, iniciar e cancelar;
  - registrar a chegada na parada e no destino;
  - enviar foto;
  - criar ou inativar local de apoio.
- **Registro:** linha na tabela "Decisões de 16 out 2026", nota de mudança na seção Movimentações, o item fora de "Pontos em aberto" e a `[decisão]` riscada no backlog.
- **Critério:** CA-246-24 em `docs/qa/criterios/T-246.md`, com o suporte Diego Santos na Moto Rápida, em "ver e editar" e em "só ver". Ele lê o quadro, a lista e a MOV-0001, e não aparece em `pessoas/` nem em `recebedores/`. Toda escrita dá 403 (nunca 500), sem gravar nada.

**Onde:** `docs/regras-de-negocio.md`, `docs/qa/criterios/T-246.md`, `tarefas/backlog.md`, `tarefas/feito.md`.
**Regras cobertas:** MOV-02, PLT-07.

**Próximo passo:**
- **Backend (T-316):** já faz A. O teste `test_plt_07_suporte_so_le_movimentacoes` cobre o CA-246-24, incluindo o local de apoio.
- **QA:** CA-246-24.
- **Orquestrador:** abrir o PR desta branch.
