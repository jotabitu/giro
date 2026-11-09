# Quadro de tarefas

O quadro é feito de arquivos para que qualquer agente, em qualquer terminal (Claude Code, Codex, OpenCode), leia e escreva o mesmo estado. O **orquestrador** é dono do quadro: cria, prioriza e distribui tarefas. Os demais agentes não editam o quadro: a tarefa anda pelo PR dela.

| Onde | Conteúdo |
| --- | --- |
| `backlog.md` | tarefas a fazer, em ordem de prioridade, e dúvidas `[decisão]` abertas. Só o orquestrador edita. |
| PRs abertos (`gh pr list`) | tarefas em andamento: abra o PR como rascunho (`--draft`) assim que pegar a tarefa |
| PRs mesclados (`gh pr list --state merged`) | tarefas entregues; a descrição do PR é o handoff |
| `backlog-arquivo.md` | decisões respondidas e tarefas riscadas até 09 nov 2026 |
| `feito.md`, `handoffs/` | registro até 09 nov 2026, congelado (T-441). Não edite. `handoffs/anexos/` continua guardando as capturas da conferência. |

## Formato de uma tarefa

```
### T-012 · Calcular acerto da devolução
- **Agente:** backend
- **Depende de:** T-010, T-011
- **Regras:** DEV-01, DEV-02, LOC-10
- **Telas:** Devolucao-Desktop, Devolucao-Mobile
- **Pronto quando:** endpoint POST /locacoes/{id}/devolucao/ devolve o acerto; teste com LOC-2836 dá R$ 183,00 a devolver.
```

## Ciclo

1. O agente pega a primeira tarefa do `backlog.md` com o nome dele e sem dependência pendente.
2. Cria a branch `t-<numero>-<slug>` a partir da `origin/develop` e abre o PR como rascunho para a `develop` (`gh pr create --draft --base develop --title "... [T-NNN]" --body-file <arquivo>`). O PR rascunho é o "em andamento".
3. Trabalha. Se travar numa dúvida de regra, avisa o **produto** pela mensagem (o produto registra a dúvida em `docs/regras/pontos-em-aberto.md`) e passa para outra tarefa.
4. Ao terminar: testes passando, `make check` limpo, descrição do PR preenchida pelo modelo `.github/pull_request_template.md`, PR fora do rascunho (`gh pr ready`).
5. Avisa quem depende dela com o link do PR. **Não edita nada em `tarefas/`.**

O orquestrador tira do `backlog.md` as tarefas entregues e as decisões respondidas, em lote, num PR próprio (`docs(tarefas): ...`), e não deixa item riscado.

### Tarefa pequena

Mudança que cabe num PR de até um dia e não mexe em modelo de dados, autenticação, permissão, pagamento nem dado pessoal pode ser feita por **um agente só** (backend ou frontend), com contrato, código, testes e tela no mesmo PR, sem passar por produto, arquiteto e segurança. Na dúvida, siga o protocolo completo (`docs/agentes/protocolo.md`).

## Fluxo de branches

Desde 29 out 2026 (`MEMORY.md`, "Fluxo com a branch develop"):

| Caso | Branch sai de | PR para | Depois do merge |
| --- | --- | --- | --- |
| Tarefa | `origin/develop` | `develop` | nada |
| Promoção de um lote | `develop` | `main` | nada |
| Correção urgente do que já está na `main` | `origin/main` (`t-<numero>-hotfix-<slug>`) | `main` | a `main` entra na `develop` |

- Todo merge é com o aval do dono, um PR por vez, com merge commit e `gh pr checks` verde.
- A promoção acontece quando um lote de tarefas fecha e o **qa** conferiu na `develop` (testes completos e, quando o lote mexe em fluxo de tela, o E2E). O PR da promoção lista as tarefas do lote.
- A `main` só aceita PR com CI verde (proteção no GitHub). Nada vai para a `main` por push direto.

## Antes do push

O CI roda uma vez por PR, como última conferência, e só nas áreas que o PR toca (backend, frontend, infra). Ele não substitui o teste local. Antes do push, e depois de `git merge origin/develop` (`origin/main` numa correção urgente):

- **Backend:** `ruff check .`, `ruff format --check .`, `mypy .` e os testes afetados. Um processo por vez: a máquina tem pouca memória.
- **Frontend:** `npm run lint`, `npm run typecheck` e os testes afetados.
- **Mudou o OpenAPI** (`docs/api/openapi.yaml`): quem mudou roda também, no frontend, `npm run api:gerar`, `npm run typecheck` e os testes afetados, e corrige no mesmo PR o que deixar de compilar. O CI roda o frontend nesse caso, e uma tela já na `develop` pode quebrar com o contrato novo (aconteceu no PR #131).

Não há CI no push da `develop` nem da `main`: toda branch recebe a base dela antes do PR, e o PR da promoção roda o CI sobre o lote inteiro.

## Handoff

O handoff é a descrição do PR, pelo modelo `.github/pull_request_template.md`. Quem recebe lê com `gh pr view <numero>`. Não crie arquivo em `tarefas/handoffs/`.

## Etiquetas

- `[decisão]` precisa de resposta do dono do produto (via agente produto).
- `[bloqueada]` depende de algo externo (parceiro de pagamento, domínio).
- `[divergência]` tela e regra discordam.
