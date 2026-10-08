# T-005 · CI · devops → orquestrador, backend, frontend, qa

**O que foi feito:** `.github/workflows/ci.yml` com três jobs em todo PR e em push na `main`:
- `backend`: Postgres 16 e Redis como services; ruff check, ruff format --check, mypy, pytest e conferência de `docs/api/openapi.yaml` contra o gerado (falha com instrução de rodar `make api-schema`);
- `frontend`: `npm ci`, `api:gerar`, lint, typecheck, vitest e build;
- `infra`: `check-env.sh` e `docker compose config`.

Os 5 pontos do handoff da T-001:
1. `backend-check` e `frontend-check` sem desvio; `backend-check` roda com o db de pé (sem `--no-deps`).
2. `MSYS_NO_PATHCONV=1` no `api-schema`.
3. `DJANGO_CORS_ALLOWED_ORIGINS` removida do `.env.example`.
4. Proxy de mesma origem: `rewrites` em `frontend/next.config.ts` (`/api/` → `API_URL_INTERNA`, com `skipTrailingSlashRedirect`) e `USE_X_FORWARDED_HOST = True` em `backend/config/settings/base.py`, para o django-tenants achar a empresa pelo Host original.
5. Beat grava o schedule em `/tmp/celerybeat-schedule`, fora do bind mount.

Também: `.gitattributes` fixa LF em `docs/api/openapi.yaml` (no Windows o CRLF do checkout fazia o diff falhar).

**Verificado:**
- Execução real no GitHub Actions (push de teste na branch, run 37668879651): os jobs passaram. O gatilho temporário foi revertido.
- Local, em containers: ruff, mypy, 88 testes e o build do frontend verdes; `docker compose up` sobe os 6 serviços.
- Proxy: `localhost:3000/api/schema/` e `admin.localhost:3000/api/schema/` dão 200; `naoexiste.localhost:3000` dá 404; `/api/docs/` dá 200.

**Não verificado:** o caso negativo do OpenAPI (CI falhando com contrato desatualizado) não foi exercitado; `make` não existe nesta máquina, então os alvos foram rodados pelos comandos equivalentes.

**Para o backend/arquiteto:** toquei `backend/config/settings/base.py` (uma linha, `USE_X_FORWARDED_HOST`). Só vale com proxy confiável na frente; em produção o proxy reverso deve sobrescrever `X-Forwarded-Host`, nunca repassar o do cliente. Segurança deve revisar. A ADR 0013 não está nesta branch; conferi só pelo comentário em `base.py`.
**Para o frontend:** o destino do rewrite é lido no build (`output: standalone`): a imagem de produção precisa de `API_URL_INTERNA` como build arg.

**O que ficou de fora:** testes ponta a ponta no merge para `main` (ainda não há Playwright no `package.json`; entra quando o qa criar), lock de dependências do backend, deploy (homologação e produção), `actions/*` ainda em v4/v5 (aviso de Node 20, sem impacto agora).
**Próximo passo para quem recebe:** orquestrador abre o PR da `t-005-ci` (inclui T-001, T-002 e T-003, que ainda não foram para a `main`); o CI roda nele. Ativar proteção de branch exigindo os 3 jobs.
