# Quadro de tarefas

O quadro é feito de arquivos para que qualquer agente, em qualquer terminal (Claude Code, Codex, OpenCode), leia e escreva o mesmo estado. O **orquestrador** é dono do quadro: cria, prioriza e distribui tarefas. Os demais agentes só movem as tarefas que são deles.

| Arquivo | Conteúdo |
| --- | --- |
| `backlog.md` | tarefas a fazer, em ordem de prioridade, e dúvidas `[decisão]` |
| `em-andamento.md` | tarefas que alguém pegou (no máximo 1 por agente) |
| `feito.md` | tarefas entregues, com link do PR |
| `handoffs/` | um arquivo por entrega: `T-012-backend.md` |

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

1. O agente pega a primeira tarefa do `backlog.md` com o nome dele e sem dependência pendente, e a move para `em-andamento.md` com a data.
2. Cria a branch `t-<numero>-<slug>` a partir da `origin/develop`.
3. Trabalha. Se travar numa dúvida de regra, escreve `[decisão]` no backlog, avisa o **produto** e passa para outra tarefa.
4. Ao terminar: testes passando, `make check` limpo, PR aberto.
5. Escreve o handoff em `handoffs/`, move a tarefa para `feito.md` e avisa quem depende dela.

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

## Modelo de handoff

```
# T-012 · Calcular acerto da devolução · backend → frontend, qa

**O que foi feito:** ...
**Onde:** backend/apps/vistorias/services.py, ...
**Contrato:** POST /api/locacoes/{id}/devolucao/ (ver docs/api/openapi.yaml)
**Regras cobertas:** DEV-01, DEV-02 (testes: test_dev_02_*)
**O que ficou de fora:** ...
**Próximo passo para quem recebe:** ...
```

## Etiquetas

- `[decisão]` precisa de resposta do dono do produto (via agente produto).
- `[bloqueada]` depende de algo externo (parceiro de pagamento, domínio).
- `[divergência]` tela e regra discordam.
