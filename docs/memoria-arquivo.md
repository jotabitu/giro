# Memória: entradas substituídas

> Entradas do `MEMORY.md` que foram substituídas por decisões posteriores (movidas na T-441). Só para consulta histórica; a decisão em vigor está no `MEMORY.md`.

## Decisões de Design

#### [2026-10-09] Sem branch develop [SUBSTITUÍDA por 2026-10-29 "Fluxo com a branch develop"]
- **Contexto:** o dono cogitou o fluxo `main` ← `develop` ← `t-xxx`, com CI nas duas etapas.
- **Decisão:** "deixe como está por enquanto": a branch da tarefa sai da `origin/main` e o PR vai para a `main`.
- **Alternativas descartadas:** `develop`, que dobraria PRs e avales.
- **Consequências:** se voltar, criar a `develop`, o CI com push nela (DevOps), atualizar `tarefas/README.md` e `CLAUDE.md` e avisar os agentes.

## Contexto de Negócio

#### [2026-10-20] Sem tarefas na tela de Veículos por enquanto [SUBSTITUÍDA por 2026-10-29 "Fase 2 aberta sem atividade iniciada"]
- O dono pediu: "não quero nenhuma tarefa por agora de alterar ou corrigir a Veiculos-Desktop e mobile". Não abrir tarefa nessas telas até ele liberar.

#### [2026-10-20] Cancelar a assinatura ativa no dia do vencimento sem pagar (T-195) [SUBSTITUÍDA por 2026-10-21 "Cancelar a ativa com o período pago já vencido"]
- Ponto em aberto, com recomendação pedida ao Produto: A, o acesso termina na hora (padrão); B, o acesso vai até o fim do período, se pago. [A CONFIRMAR] O PR da T-195 espera a revisão de Segurança T-199 antes do merge.
