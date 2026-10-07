# Agentes do Giro

Este arquivo é lido por agentes que não usam o formato do Claude Code (Codex, OpenCode e outros). As regras gerais do projeto estão em `CLAUDE.md` e valem para todos: leia esse arquivo primeiro.

## Quem é quem

Cada função tem um arquivo com missão, leituras obrigatórias, responsabilidades, o que não fazer e o critério de pronto. Ao iniciar, assuma **uma** função e leia o arquivo dela.

| Agente | Arquivo | Cuida de | Pasta onde escreve |
| --- | --- | --- | --- |
| orquestrador | `.claude/agents/orquestrador.md` | prioridades, distribuição e revisão de entregas | `tarefas/` |
| produto | `.claude/agents/produto.md` | regras de negócio, critérios de aceite, dúvidas | `docs/regras-de-negocio.md`, `docs/plano.md` |
| arquiteto | `.claude/agents/arquiteto.md` | modelo de dados, contratos da API, ADRs | `docs/decisoes/`, `docs/api/` |
| backend | `.claude/agents/backend.md` | Django, DRF, Celery, testes de regra | `backend/` |
| frontend | `.claude/agents/frontend.md` | Next.js, páginas, integração com a API | `frontend/` (exceto `src/design-system/`) |
| design-system | `.claude/agents/design-system.md` | tokens, componentes, marca, telas de referência | `frontend/src/design-system/`, `docs/design-system/`, `docs/telas/`, `docs/marca/` |
| qa | `.claude/agents/qa.md` | seed, testes de aceitação e ponta a ponta | `backend/tests/aceitacao/`, `backend/seed/`, `frontend/e2e/`, `docs/qa/` |
| devops | `.claude/agents/devops.md` | Docker, CI/CD, ambientes, backups | `infra/`, `.github/`, `docker-compose.yml`, `Makefile` |
| seguranca | `.claude/agents/seguranca.md` | autenticação, permissões, LGPD, auditoria | `docs/seguranca/` (e tarefas no backlog) |

Cada agente escreve só na sua pasta. Para mudar algo de outra função, abra uma tarefa ou fale com o dono.

## Como começar

```
Você é o agente <nome> do projeto Giro.
Leia CLAUDE.md e .claude/agents/<nome>.md, depois tarefas/backlog.md.
Pegue a primeira tarefa com o seu nome que não tenha dependência pendente.
```

O fluxo de tarefas e o modelo de handoff estão em `tarefas/README.md`. A forma como os agentes conversam está em `docs/agentes/protocolo.md`.
