# Giro

Sistema de gestão para locadoras e revendas de motos e carros, vendido como SaaS white label: cada empresa usa o sistema com a própria marca, e o Giro aparece só no painel da plataforma, na compra e na implantação.

## Estrutura

```
giro/
├── CLAUDE.md              regras para todos os agentes (leia primeiro)
├── AGENTS.md              quem é quem, para Codex e outros agentes
├── .claude/agents/        uma função por arquivo (orquestrador, produto, arquiteto,
│                          backend, frontend, design-system, qa, devops, seguranca)
├── docs/
│   ├── regras-de-negocio.md   fonte única da lógica de negócio, com códigos de regra
│   ├── plano.md               visão, módulos, arquitetura e roadmap
│   ├── design-system/         tokens, componentes, wl-theme.css
│   ├── telas/                 123 telas de referência (html/) e o índice por módulo
│   ├── marca/                 marca Giro e kit de logotipo
│   ├── decisoes/              ADRs e modelo de dados
│   ├── api/                   contratos e OpenAPI
│   └── agentes/               protocolo entre agentes e montagem no Maestri
├── backend/               Django 5 + DRF + django-tenants (um README por app)
├── frontend/              Next.js + TypeScript + Tailwind + shadcn/ui
├── infra/                 Docker, deploy, backups
├── .github/workflows/     CI
└── tarefas/               quadro de tarefas compartilhado pelos agentes
```

## Para começar

1. Crie o repositório: `git init && git add . && git commit -m "chore: estrutura inicial"` (os agentes usam branches e worktrees).
1. Leia `CLAUDE.md`.
2. Para orquestrar com agentes no Maestri, siga `docs/agentes/maestri.md`.
3. Para ver as telas, abra `docs/telas/README.md` e clique em qualquer tela (abre direto no navegador).

Depois que as tarefas T-001 a T-003 forem entregues:

```
cp .env.example .env
make up
make seed
```
