# Montando o time no Maestri

O Maestri é um canvas onde cada nó é um terminal com um agente (Claude Code, Codex, OpenCode ou shell), e os agentes podem mandar mensagens uns aos outros. Este repositório já traz tudo o que eles precisam: as regras gerais em `CLAUDE.md` e `AGENTS.md`, e uma função por arquivo em `.claude/agents/`.

## Layout sugerido no canvas

```
                 ┌──────────────┐
                 │ orquestrador │
                 └──────┬───────┘
        ┌───────────────┼────────────────┐
  ┌─────┴────┐    ┌─────┴─────┐    ┌─────┴─────┐
  │ produto  │    │ arquiteto │    │ seguranca │
  └──────────┘    └─────┬─────┘    └───────────┘
              ┌─────────┼──────────┐
        ┌─────┴───┐ ┌───┴──────┐ ┌─┴─────────────┐
        │ backend │ │ frontend │ │ design-system │
        └─────┬───┘ └───┬──────┘ └───────────────┘
              └────┬────┘
               ┌───┴──┐   ┌────────┐
               │  qa  │   │ devops │
               └──────┘   └────────┘
```

Não precisa abrir os nove de uma vez. Uma boa sequência:

| Momento | Terminais abertos |
| --- | --- |
| Fase 0 (fundação) | orquestrador, arquiteto, devops, design-system |
| Fase 1 (MVP) | orquestrador, produto, arquiteto, backend, frontend, qa |
| Fim de cada fase | + seguranca |

Use Claude Code para orquestrador, produto, arquiteto e backend (aproveitam os subagentes de `.claude/agents/`). Frontend, design-system, qa e devops podem rodar em Claude Code ou Codex; o Codex lê `AGENTS.md`.

## Mensagem inicial de cada terminal

Cole no terminal ao criar o nó, trocando o nome:

```
Você é o agente orquestrador do projeto Giro.
Leia CLAUDE.md e .claude/agents/orquestrador.md, depois tarefas/README.md e tarefas/backlog.md.
Os outros agentes neste canvas são: produto, arquiteto, backend, frontend, design-system, qa, devops, seguranca.
Comece distribuindo as tarefas da fase 0.
```

```
Você é o agente backend do projeto Giro.
Leia CLAUDE.md e .claude/agents/backend.md, depois tarefas/backlog.md.
Pegue a primeira tarefa com o seu nome sem dependência pendente. Ao terminar, escreva o handoff e avise o orquestrador.
```

O mesmo vale para os demais: `produto`, `arquiteto`, `frontend`, `design-system`, `qa`, `devops`, `seguranca`.

## Um repositório, várias cópias

Agentes que escrevem código ao mesmo tempo (backend, frontend, design-system, qa) devem trabalhar em worktrees separados para não pisar um no outro:

```
git worktree add ../giro-backend  -b t-001-esqueleto-backend
git worktree add ../giro-frontend -b t-002-esqueleto-frontend
```

Abra o terminal de cada agente dentro do worktree dele. Orquestrador, produto e arquiteto podem ficar na cópia principal.

## Sua parte, como dono do produto

- Responder as `[decisão]` que o agente produto juntar em "Pontos em aberto" das regras.
- Aprovar os PRs que o orquestrador marcar como prontos.
- Quando desenhar telas novas, colocar o HTML em `docs/telas/html/` e pedir ao design-system para atualizar o índice.
