# T-318 · Suporte Giro nas movimentações · produto → orquestrador, segurança (T-315), backend

Pergunta da segurança na T-315 (PR #328, `tarefas/handoffs/T-315-seguranca.md`): o suporte Giro em "ver e editar" pode criar e conduzir uma movimentação?

**O que a regra já responde:** o suporte nunca leva nem recebe. A `MOV-02` pede "usuário ativo ligado à filial", e o suporte não é usuário da empresa (ADR 0013, `AtorSuporte` sem `contas.Usuario`). Ele também não aparece em `pessoas/` nem em `recebedores/`. Isso agora está escrito na `MOV-02`, com nota T-318.

**O que a regra não responde: `[decisão]`** (backlog e "Pontos em aberto"). A `PLT-07` deixa o suporte em "ver e editar" editar, e ele age como administrador; não há exceção para a movimentação, como há para "Copiar link do convite".
- A) Não. Mesmo em "ver e editar", o suporte só lê. Recebem 403 `PLT-07`: criar, editar, iniciar, cancelar, registrar a chegada na parada e no destino, enviar foto e criar ou inativar local de apoio.
- B) Sim, como administrador, nunca como quem leva nem quem recebe, com o ator suporte na auditoria.
- **Padrão: A**, o mesmo da segurança. Até a resposta, vale o padrão.

**Onde:** `docs/regras-de-negocio.md` (`MOV-02`, nota T-318, Pontos em aberto), `tarefas/backlog.md`, `tarefas/feito.md`.
**Regras cobertas:** MOV-02, PLT-07.

**Próximo passo:**
- **Orquestrador:** levar a `[decisão]` ao dono e abrir o PR desta branch. Com a resposta, o produto põe a regra na `MOV-02` e o critério CA-246 com a Moto Rápida.
- **Backend (tarefa da T-315):** com o padrão A, `suporte_proibido = True` em todas as escritas das movimentações, incluindo o local de apoio.
