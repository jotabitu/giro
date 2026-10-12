# Infraestrutura

Dono: agente **devops**. Leia `.claude/agents/devops.md`.

```
infra/
├── docker/        Dockerfiles de backend (também worker e beat) e frontend, entrypoint do backend
├── postgres/      SQL de inicialização do banco: papéis da ADR 0016 (01-papeis.sh)
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
- `python manage.py spectacular --urlconf config.urls_openapi --file ... --validate` gera o OpenAPI das rotas da empresa e da plataforma (alvo `make api-schema`, grava em `docs/api/openapi.yaml`).
- WeasyPrint: a imagem já traz pango, harfbuzz e fontes. Dependência de sistema nova vai para `infra/docker/backend.Dockerfile`.

## O que o frontend precisa respeitar (T-002)

- `frontend/package.json` e `frontend/package-lock.json` versionado (o Dockerfile usa `npm ci`). Node 22.
- Scripts: `dev` (servidor Next; o Compose passa `--hostname 0.0.0.0 --port 3000`), `lint`, `typecheck`, `test` (Vitest), `build` e `api:gerar` (cliente tipado a partir de `docs/api/openapi.yaml`).
- `make frontend-check` executa `npm run lint && npm run typecheck && npm test -- --run && npm run build`.
- Chamadas do navegador usam URL relativa (`/api/`, mesma origem; `NEXT_PUBLIC_API_URL` fica vazia); chamadas do servidor Next usam `API_URL_INTERNA`. Nunca coloque segredo em variável `NEXT_PUBLIC_*`.
- `node_modules` e `.next` ficam em volumes nomeados, não no host. Dependência nova: rebuild com `docker compose build frontend`.

## Ainda não coberto por esta tarefa

CI (T-005), homologação e produção, certificado curinga, backup e Sentry no frontend ficam em tarefas próprias.

## Containers parados no dev (T-099)

Todos os serviços do `docker-compose.yml` têm `restart: unless-stopped`: voltam sozinhos se o processo cair ou o Docker reiniciar. **Não voltam** se alguém os parar de propósito (`docker compose stop`, `make down`, `docker stop`); é o que `unless-stopped` quer dizer.

**Caso de 08 e 09/10 (frontend com `npm error signal SIGTERM`).** Não foi falha do Next: `OOMKilled=false`, `ExitCode=0`, sem erro antes do SIGTERM no log. Em 09/10 os seis containers do projeto `giro` pararam entre 12:12:27Z e 12:12:31Z, na ordem inversa das dependências (frontend, beat, backend e worker, depois db e redis; db e redis saíram com 0, o worker com 137 por não encerrar a tempo). Essa sequência é a de um `docker compose stop` ou `down` no projeto, não a de uma queda. O Docker Desktop (iniciado em 08/10 10:57) e o Windows (boot de 08/10 10:49) não reiniciaram nesse intervalo. Quem emitiu o comando não dá para saber pelos containers.

**Causa provável (hipótese, não provada):** o Compose nomeia o projeto pela pasta. Um `make up`, `make down` ou `make check` rodado em qualquer pasta chamada `giro` (a cópia principal, ou o worktree que o orquestrador usa) mexe nos mesmos containers e volumes de quem está com o ambiente de pé. Os containers `backend`, `worker` e `beat` foram recriados em 09/10 08:24, sinal de outro `up` no mesmo projeto.

**Como evitar:**
- Agente que só precisa testar usa outro nome e outras portas, por exemplo `COMPOSE_PROJECT_NAME=giro-<agente> PORTA_BACKEND=18000 PORTA_FRONTEND=13000 PORTA_POSTGRES=15432 PORTA_REDIS=16379 make backend-check`. `make down` só no projeto que você mesmo subiu.
- Se o ambiente parou, `docker compose -p giro start` volta os containers existentes sem recriar.
- Para saber quem parou, na hora: `docker events --since 10m --filter container=<nome>` mostra o `kill`/`stop` e o ator do comando; `docker inspect <nome> --format '{{.State.FinishedAt}} {{.State.ExitCode}} {{.State.OOMKilled}}'` separa queda de parada.

## Papéis de banco (ADR 0016, T-043)

| Papel | Uso | Variável |
| --- | --- | --- |
| `giro_migracao` | dono dos schemas e tabelas; `migrate_schemas` e criação de schema de empresa | `DATABASE_URL_MIGRACAO` |
| `giro_app` | requisições Django e Celery; sem DDL; auditoria só `SELECT` e `INSERT` | `DATABASE_URL` |
| `giro_expurgo` | dono da função `auditoria_expurgar` (sem login) | nenhuma |

`infra/postgres/01-papeis.sh` cria os três, dá a `giro_migracao` o schema `public` e `CREATE` no banco, e deixa `giro_app` com `SELECT/INSERT/UPDATE/DELETE` por privilégio padrão no `public`. Roda só quando o volume do Postgres é criado (`make down V=1` para refazer). Testado num Postgres 16 limpo: `giro_app` não cria tabela nem schema e lê e escreve em tabela criada por `giro_migracao`.

**Dev:** `DATABASE_URL` e `DATABASE_URL_MIGRACAO` apontam para o superusuário do container (ADR 0016, item 5); os valores com papéis separados estão comentados em `.env.example`.

**O que o backend precisa fazer (ainda não feito):**
- Ler `DATABASE_URL_MIGRACAO` e usá-la em `migrate_schemas` e em `plataforma.services.criar_empresa`; o entrypoint (`backend-entrypoint.sh`) deve migrar com ela.
- A rotina que cria o schema de empresa aplica os `GRANT` do schema (`ALTER DEFAULT PRIVILEGES` para `giro_app`, `REVOKE UPDATE, DELETE, TRUNCATE` na auditoria) e cria `auditoria_expurgar` com dono `giro_expurgo`.
- Os testes de imutabilidade sobem com `giro_app`.

**Ambientes (homologação e produção):** rodar o mesmo SQL no banco gerenciado, com senhas geradas e guardadas no cofre do ambiente, nunca as de dev. Credencial de `giro_migracao` só no job de deploy; `giro_app` no serviço em execução.

`giro_migracao` é membro de `giro_expurgo` (`GRANT giro_expurgo TO giro_migracao`, T-052): o `post_migrate` do backend roda como `giro_migracao` e faz `ALTER FUNCTION auditoria_expurgar ... OWNER TO giro_expurgo`, que exige ser membro do papel novo dono. Em banco gerenciado, aplicar o mesmo `GRANT`; o volume de dev já criado precisa de `make down V=1` ou do `GRANT` à mão.

**CI:** continua com um papel só. Passa a usar os papéis separados no mesmo PR em que o backend ler `DATABASE_URL_MIGRACAO` (job `backend` ganha o `01-papeis.sh` no service Postgres).

## IP do ator e proxies (ADR 0018, item 4, T-045)

- O backend só confia no `X-Forwarded-For` quando `REMOTE_ADDR` está numa rede de `GIRO_REDES_PROXY` (CIDR, por ambiente); aí pega o IP contando `GIRO_PROXIES_CONFIAVEIS` da direita. Sem o cabeçalho, ou de fora dessas redes, vale `REMOTE_ADDR`.
- **Homologação e produção:** o proxy reverso manda `/api/` direto ao Django, sem passar pelo Next. Ele acrescenta o IP do cliente (não repassa o que veio). `GIRO_PROXIES_CONFIAVEIS=1` e `GIRO_REDES_PROXY` = rede do proxy reverso. O Django só pode ser alcançável pelo proxy (regra de rede do ambiente, a fechar no deploy). O rewrite e o middleware do Next ficam fora desse caminho: se `/api/` passasse pelo Next, o middleware apagaria o IP que o proxy acrescentou.
- **Dev:** o proxy de mesma origem é o rewrite do Next, que repassa o `X-Forwarded-For` do cliente sem acrescentar o IP real (medido). Por isso `frontend/src/middleware.ts` descarta o cabeçalho em `/api/`: um valor forjado não chega ao Django (testado com `X-Forwarded-For: 6.6.6.6`). Em dev o ator aparece com o endereço do container do frontend. `GIRO_REDES_PROXY` em dev cobre as faixas privadas do Docker.

Nota para a subida do Next: no Next 16 `middleware.ts` passa a se chamar `proxy.ts`; mover `frontend/src/middleware.ts` quando a versão subir. O destino do rewrite é lido no build (`output: standalone`) e, em `next dev`, em execução.

## Endurecimento de produção (T-035)

Valores por ambiente (o processo precisa de `DJANGO_SETTINGS_MODULE`; `wsgi.py`, `asgi.py` e `config/celery.py` não têm mais padrão e falham sem ele, C-04):

| Variável | dev | homologação | produção |
| --- | --- | --- | --- |
| `DJANGO_SETTINGS_MODULE` | `config.settings.dev` | `config.settings.prod` | `config.settings.prod` |
| `JWT_SIGNING_KEY` | ausente ou vazia (usa `DJANGO_SECRET_KEY`) | obrigatória, própria; vazia é recusada | obrigatória, própria; vazia é recusada |
| `GIRO_PROXIES_CONFIAVEIS` | 1 (Next) | 1 (proxy reverso) | 1 (proxy reverso) |
| `GIRO_REDES_PROXY` | faixas privadas do Docker | rede do proxy reverso | rede do proxy reverso |
| `GIRO_CHAVE_DADOS_PESSOAIS`, `GIRO_CHAVE_SEGREDOS`, `GIRO_PEPPER_HMAC` | valores de exemplo do `.env.example` (ausente ou vazia cai neles) | obrigatórios, próprios, do cofre; vazios são recusados | obrigatórios, próprios, do cofre; vazios são recusados |

Modelos de homologação e produção, só com o que difere do dev: `infra/deploy/homologacao.env.example` e `infra/deploy/producao.env.example`. A `GIRO_REDES_PROXY` deles é um exemplo (`10.20.0.0/24`, `10.10.0.0/24`) e deve ser trocada pela sub-rede real do proxy reverso quando o ambiente existir; `prod.py` recusa lista vazia, rede inválida e `/0`.
| `DJANGO_HSTS_SEGUNDOS` / `DJANGO_HSTS_PRELOAD` | não se aplica | curto / 0 até estabilizar | 31536000 / 1 |
| `GIRO_EXPOR_DOCUMENTACAO_DA_API` | aberto | 0 (aberto só se pedido) | 0 |

`prod.py` recusa subir se `JWT_SIGNING_KEY` faltar ou igualar `DJANGO_SECRET_KEY`, ou se `GIRO_REDES_PROXY` estiver vazia, inválida ou aberta (`/0`). Pela R-03 da revisão T-050 (T-052), recusa também: chave ou pepper com o valor do `.env.example` (a chave é comparada sem o id, então trocar só o `1:` não passa), a mesma chave em `GIRO_CHAVE_DADOS_PESSOAIS` e `GIRO_CHAVE_SEGREDOS`, chave que não decodifica para 32 bytes, pepper com menos de 32 bytes e pepper igual a `DJANGO_SECRET_KEY` ou `JWT_SIGNING_KEY`. Testes `test_r03_*` em `backend/tests/test_producao.py`. Fixa `SHOW_PUBLIC_IF_NO_TENANT_FOUND = False` (host desconhecido dá 404, S-16), HSTS com preload e subdomínios, `Referrer-Policy: same-origin` e `X-Frame-Options: DENY` (S-18).

Frontend: `next.config.ts` envia `Referrer-Policy`, `X-Frame-Options`, `X-Content-Type-Options`, `Permissions-Policy` e HSTS; `src/middleware.ts` envia a CSP com nonce por requisição (`src/lib/csp.ts`), e o layout raiz é `force-dynamic` para o nonce chegar aos scripts do Next (página pré-renderizada ficava sem nonce, medido). Sentry no frontend, quando entrar, precisa abrir `connect-src`.

**CSP, avaliação da T-052 (sem mudança de código):** (1) `img-src`: hoje nenhuma tela carrega imagem externa e o contrato de arquivos ainda não definiu o host do S3. O caminho recomendado é o frontend ler a origem de `S3_ENDPOINT_URL` (ou do host do bucket) no `middleware.ts`, em execução, e acrescentá-la a `img-src` (e `frame-src` se houver PDF embutido) quando a T-012/T-014 trouxerem logo, foto e prévia; a alternativa é o Django servir o arquivo pela mesma origem. (2) `connect-src 'self'`: certo, porque `NEXT_PUBLIC_API_URL` fica vazia em todos os ambientes (cookie `__Host-`, ADR 0013); o Sentry do frontend vai precisar do host do DSN. (3) `force-dynamic` na raiz: aceito; os arquivos de `_next/static` continuam com cache longo, só o HTML deixa de ser estático, e o app é autenticado. Registrar no PR.

**Fica para o deploy (regra de rede):** o Django só alcançável pelo proxy reverso, que deve também sobrescrever `X-Forwarded-For` e `X-Forwarded-Proto` e repassar `Host`. Sem isso `GIRO_REDES_PROXY` não protege.
