# Infraestrutura

Dono: agente **devops**. Leia `.claude/agents/devops.md`.

```
infra/
├── docker/        Dockerfiles de backend, worker e frontend
├── deploy/        homologação e produção (a definir em ADR: AWS, GCP ou VPS)
└── backup/        scripts de backup diário e teste de restauração
```

Na raiz ficam `docker-compose.yml`, `Makefile` e `.env.example` (tarefa T-003) e `.github/workflows/` (tarefa T-005).

Domínios: `admin.girolocadoras.com.br` (plataforma) e `<subdominio>.girolocadoras.com.br` (empresas). Domínio decidido em 07 out 2026 (ver regras); mesmo assim, tudo configurável por variável de ambiente.
