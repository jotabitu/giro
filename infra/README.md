# Infraestrutura

Dono: agente **devops**. Leia `.claude/agents/devops.md`.

```
infra/
├── docker/        Dockerfiles de backend (também worker e beat) e frontend, entrypoint do backend
├── scripts/       verificações de infra (check-env.sh)
├── deploy/        homologação e produção (a definir em ADR: AWS, GCP ou VPS)
└── backup/        scripts de backup diário e teste de restauração
```

Na raiz ficam `docker-compose.yml`, `Makefile` e `.env.example` (tarefa T-003) e `.github/workflows/` (tarefa T-005).

Domínios: `admin.girolocadoras.com.br` (plataforma) e `<subdominio>.girolocadoras.com.br` (empresas). Domínio decidido em 07 out 2026 (ver regras); mesmo assim, tudo configurável por variável de ambiente.

## Subir o ambiente

```
make up        # cria .env a partir de .env.example, constrói e sobe tudo
make seed      # empresa Moto Rápida
make check     # infra, backend e frontend
make down      # para (make down V=1 apaga os volumes, inclusive o banco)
```

Serviços do `docker-compose.yml`: `db` (Postgres 16), `redis`, `backend` (runserver; roda `migrate_schemas` ao iniciar), `worker` (Celery), `beat` (Celery Beat), `frontend` (Next.js em modo dev). Código por bind mount: editar no host recarrega no container.

Em dev, `admin.localhost:3000` e `<subdominio>.localhost:3000` resolvem para a máquina (navegadores modernos). O domínio vem de `DOMINIO_BASE`.

No Windows, `make` não vem instalado: use Git Bash ou WSL, ou rode os comandos de `docker compose` direto.

`make check` roda `infra-check` (todo `${VAR}` do Compose existe em `.env.example` e o Compose é válido), `backend-check` e `frontend-check`. Enquanto `backend/manage.py` e `frontend/package.json` não existirem, os dois últimos avisam e passam; o desvio sai do `Makefile` quando T-001 e T-002 entregarem.

## O que o backend precisa respeitar (T-001)

- `backend/manage.py`, pacote de configuração `config` (`config.settings.dev` é o padrão via `DJANGO_SETTINGS_MODULE`) e `config/celery.py` com o app Celery, para `celery -A config worker` e `celery -A config beat` funcionarem.
- `backend/requirements.txt` (produção) e `backend/requirements-dev.txt` (começa com `-r requirements.txt`; ruff, mypy, pytest). O Dockerfile instala só esses dois.
- Ler a configuração das variáveis de `.env.example`: `DATABASE_URL`, `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DOMINIO_BASE`, `SUBDOMINIO_PLATAFORMA`, `SENTRY_DSN_BACKEND`. Variável nova entra em `.env.example` no mesmo PR.
- Banco com `django_tenants.postgresql_backend`. O entrypoint roda `migrate_schemas --shared` e `--tenant` quando `RODAR_MIGRACOES=1` (só o serviço `backend`).
- `ALLOWED_HOSTS` aceita `.localhost` e `backend` (nome do serviço na rede do Compose).
- Comando `python manage.py seed_moto_rapida` (alvo `make seed`; o agente qa mantém o seed).
- `make backend-check` executa `ruff check . && ruff format --check . && mypy . && pytest -q` em `backend/`. Se preferir outra ferramenta, avise o devops.
- `python manage.py spectacular --file ... --validate` gera o OpenAPI (alvo `make api-schema`, grava em `docs/api/openapi.yaml`).
- WeasyPrint: a imagem já traz pango, harfbuzz e fontes. Dependência de sistema nova vai para `infra/docker/backend.Dockerfile`.

## O que o frontend precisa respeitar (T-002)

- `frontend/package.json` e `frontend/package-lock.json` versionado (o Dockerfile usa `npm ci`). Node 22.
- Scripts: `dev` (servidor Next; o Compose passa `--hostname 0.0.0.0 --port 3000`), `lint`, `typecheck`, `test` (Vitest), `build` e `api:gerar` (cliente tipado a partir de `docs/api/openapi.yaml`).
- `make frontend-check` executa `npm run lint && npm run typecheck && npm test -- --run && npm run build`.
- Chamadas do navegador usam `NEXT_PUBLIC_API_URL`; chamadas do servidor Next usam `API_URL_INTERNA`. Nunca coloque segredo em variável `NEXT_PUBLIC_*`.
- `node_modules` e `.next` ficam em volumes nomeados, não no host. Dependência nova: rebuild com `docker compose build frontend`.

## Ainda não coberto por esta tarefa

CI (T-005), homologação e produção, certificado curinga, backup e Sentry no frontend ficam em tarefas próprias.
