# Infraestrutura

Dono: agente **devops**. Leia `.claude/agents/devops.md`.

```
infra/
├── docker/        Dockerfiles de backend (também worker e beat) e frontend, entrypoint do backend
├── postgres/      SQL de inicialização do banco: papéis da ADR 0016 (01-papeis.sh)
├── scripts/       verificações de infra (check-env.sh)
├── deploy/        homologação e produção (uma VPS com tudo em Docker Compose, de preferência num provedor no Brasil: ADR 0033, opção B)
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

**Onde a `DATABASE_URL_MIGRACAO` entra (T-352, achado B-01 da T-199):** só no `worker` do Celery, nunca no `backend` (web) nem no `beat`.
- **Por quê:** é credencial com DDL em todos os schemas. A única rotina de execução que a usa é a `plataforma.aud_08_apagar_empresas` (`DROP SCHEMA` da empresa cancelada, ADR 0025), que roda no worker. O web, que atende a internet, e o beat, que só agenda, não precisam dela; sem ela, um furo no web não ganha DDL. Sem a variável no worker, a tarefa só registra um log de erro e a empresa fica para o dia seguinte.
- **Desenvolvimento:** vem do `.env` (modelo em `.env.example`). O `docker-compose.yml` a zera (`DATABASE_URL_MIGRACAO: ""`) no `backend` e no `beat`; o `worker` a lê do `env_file`.
- **Homologação:** `infra/deploy/docker-compose.homologacao.yml` a passa ao `worker` (`DATABASE_URL_MIGRACAO: ${DATABASE_URL_MIGRACAO}`, do cofre) e a zera no `backend`, no `beat` e no `estaticos`. O `migrar` continua com ela para o `migrate_schemas`. Em produção vale o mesmo desenho; o cofre (`producao.env.example`) traz a variável com a do `giro_migracao`.
- **Por que zerar e não omitir:** o arquivo de variáveis do cofre é o mesmo para todos os serviços (`env_file`), então a variável chegaria a todos. `environment:` vence o `env_file`.
- **CI:** o job Infra roda `infra/scripts/check-migracao-so-no-worker.sh`, que falha se o `backend` ou o `beat` receber a variável, ou se o `worker` não a receber, nos dois compose.

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

## Proxy reverso (T-158, M-04)

Modelo em `infra/proxy/giro.conf.template` (nginx; a imagem oficial troca as variáveis `DOMINIO_BASE`, `BACKEND_UPSTREAM`, `FRONTEND_UPSTREAM` e `CERT_DIR` ao subir; `nginx -t` passa com a imagem 1.27). O produto do proxy ainda depende da ADR de deploy; se for outro, ele precisa cumprir esta lista antes de homologação:

- [ ] Corpo de até 12 MB (`client_max_body_size 12m`; 413 acima). O Django não limita arquivo em multipart e `comum/arquivos.validar` só confere depois de receber tudo. O webhook tem 1 MB.
- [ ] `X-Forwarded-Host`, `X-Forwarded-Proto` e `X-Forwarded-For` **sobrescritos** pelo proxy (`$host`, `$scheme`, `$remote_addr`), nunca repassados do cliente; `Forwarded` apagado. O `TenantMainMiddleware` escolhe a empresa por `get_host()`, que segue o `X-Forwarded-Host`.
- [ ] `X-Forwarded-For` com um só valor (o IP da conexão), para `GIRO_PROXIES_CONFIAVEIS=1`. Com balanceador na frente, o proxy deve confiar nele (`set_real_ip_from`/`real_ip_header`) e o valor de `GIRO_PROXIES_CONFIAVEIS` e de `GIRO_REDES_PROXY` acompanha a cadeia real.
- [ ] `/api/` vai direto ao Django, sem passar pelo Next; o Django só é alcançável pelo proxy (regra de rede do ambiente).
- [ ] Rate limit de borda: `/api/auth/` (10 por minuto por IP, rajada de 10) e `/api/webhooks/` (120 por minuto, rajada de 60), resposta 429. Soma-se aos limites da aplicação, não os substitui.
- [ ] Host desconhecido recusado no proxy (444); HTTP redireciona para HTTPS; certificado curinga.
- [ ] Backend: `USE_X_FORWARDED_HOST` é `False` em `base.py` e `test.py`, e `True` só em `dev.py` (o rewrite do Next) e `prod.py`. Teste `test_t158_x_forwarded_host_so_em_dev_e_prod`.

## Servidor da aplicação e leitura de PDF (T-258)

Homologação e produção sobem a imagem `producao` do `infra/docker/backend.Dockerfile` (ADR 0027, T-264): só `requirements.txt` (com o `gunicorn`), usuário `giro` sem root, `collectstatic` feito no build e `CMD gunicorn -c /app/gunicorn.conf.py config.wsgi:application`, com o `infra/docker/gunicorn.conf.py` da T-258. Worker e beat usam a mesma imagem com o comando deles. O alvo `dev` (requirements-dev, root, `runserver` com o código por bind mount) é o do `docker-compose.yml`; o Dockerfile sem `--target` produz o `dev`, então todo uso de homologação ou produção pede `--target producao`.

`infra/deploy/docker-compose.homologacao.yml` sobe `estaticos`, `migrar`, `backend`, `worker`, `beat` e o `proxy` (nginx com `infra/proxy`). Banco, Redis e frontend ficam fora, por variável. O `migrar` roda `migrate_schemas` com `DATABASE_URL_MIGRACAO` e sai; o backend, o worker e o beat só sobem depois e usam `DATABASE_URL` (`giro_app`, sem DDL). É o mesmo cuidado de "uma migração por deploy" da ADR, com a credencial separada.

**Estáticos do Admin (decisão do devops, ADR 0027):** o proxy serve `/static/` a partir de um volume, sem dependência nova (nada de whitenoise). O `collectstatic` roda no build da imagem; o serviço `estaticos` copia `/app/staticfiles` para o volume a cada subida (um volume nomeado só se preencheria na primeira vez), e o `proxy` o monta somente leitura. Só os estáticos do Django passam por aí; os do Next ficam em `/_next/static/`. O Django Admin da plataforma é alcançado por `admin.<domínio>/admin/`, fechado por lista de IPs (T-291): ver "Como abrir o Admin".

**Teste de subida:** `sh infra/scripts/teste-subida-producao.sh` (Docker com Compose v2) builda o alvo `producao`, sobe o compose de homologação com banco e Redis descartáveis e as variáveis do `homologacao.env.example`, e confere: o processo 1 é o Gunicorn com 2 workers `gthread` e 4 threads; roda sem root e sem pytest; uma requisição pelo proxy chega ao Django; o estático do Admin sai pelo proxy; worker e beat de pé; e `docker stop` deixa terminar uma requisição de 8 s e sai com código 0. Passou em 16 out 2026 (17 conferências), com os papéis separados: a migração entra como `giro_migracao` (o serviço `migrar`) e o backend como `giro_app` (a T-276 corrigiu a troca de dono da função de expurgo da auditoria, que falhava com `permission denied for schema public`). Em banco gerenciado, aplicar o mesmo SQL do `infra/postgres/01-papeis.sh`, inclusive `ALTER SCHEMA public OWNER TO giro_migracao` e `GRANT giro_expurgo TO giro_migracao`.

**Por que isso importa para a ADR 0026:** a leitura do CRLV-e e da CNH-e espera um processo filho por até 8 s de relógio, dentro da requisição.

| Camada | Valor | Observação |
| --- | --- | --- |
| Gunicorn `timeout` | 30 s (3,75 vezes os 8 s) | Valor global: o Gunicorn não tem limite por rota. No `gthread` ele só mata worker que parou de responder ao mestre, não corta requisição lenta. |
| Proxy, leitura (`/api/veiculos/leitura-crlv/`, `/api/clientes/leitura-cnh/`) | 20 s de leitura e envio, corpo de 3 MB, 20 requisições por minuto por IP (rajada de 5) | É o corte por requisição. O arquivo lido tem até 2 MB. |
| Proxy, resto de `/api/` | 60 s, corpo de 12 MB | Como estava na T-158: nenhuma outra rota ficou mais frouxa. |

Conferido com `nginx -t` e com um servidor de mentira atrás do proxy (1,27): corpo de 2,8 MB passa na rota de leitura, 4 MB dá 413 nela e na CNH-e, 4 MB passa em `/api/veiculos/`, 13 MB dá 413; passada a rajada, 429. O salvar do veículo com o PDF anexado (até 10 MB, ADR 0026) não é a rota de leitura e vale os 12 MB.

**Workers e memória** (estimativa; o código da leitura ainda não existe, então nada abaixo foi medido com o filho real):

- Cada leitura em andamento custa até 512 MB de espaço de endereço no filho (`RLIMIT_AS`, que é virtual: o consumo real do `pypdf` num PDF de 500 KB deve ser bem menor) mais o worker que espera. O worker do Django em desenvolvimento ocupa cerca de 140 MiB parado (`docker stats`, `runserver`, medido em 15 out); em produção conte 250 a 300 MiB por worker, valor assumido.
- `gthread` com threads deixa qualquer requisição abrir um filho, então o pior caso é workers vezes threads leituras ao mesmo tempo. Os limites da aplicação (30 por hora por usuário, 200 por hora por empresa) e os da borda tornam isso raro, mas não impossível.
- Homologação: 2 workers, 4 threads, contêiner com 2 GiB (2 × 300 MiB mais 2 filhos de 512 MiB cabem; 8 filhos não). Produção: 3 workers, 4 threads, 4 GiB (3 × 300 MiB mais 5 filhos). Os dois números assumem que a leitura simultânea fica em 2 a 5 por vez.
- **Pedido ao backend:** limitar as leituras simultâneas por processo (um semáforo de 2) e devolver 429 ou 503 `leitura_ocupada` quando cheio. Com isso o pior caso deixa de depender de workers vezes threads e o teto de memória fica fechado. Medir o filho real (RSS de pico num CRLV-e e numa CNH-e fictícios) assim que o parser existir e rever esta tabela.
- O filho não precisa de rede (ADR 0026, item 5). Fechar a rede dele pelo contêiner (política de rede ou usuário sem rota) é pergunta aberta da segurança; o devops espera a resposta.

## Senha no Postgres e no Redis (T-274)

Condição da segurança na T-247 (o processo filho da leitura de PDF roda sem rede fechada): em homologação e produção, banco e Redis só com senha.

- **Backend:** `prod.py` recusa subir com `DATABASE_URL` sem senha e com `REDIS_URL`, `CELERY_BROKER_URL` ou `CELERY_RESULT_BACKEND` sem senha (a ausência de qualquer uma cai no padrão de `base.py`, sem senha, e também é recusada). Testes `test_t274_*` em `backend/tests/test_producao.py`.
- **Cofre** (`infra/deploy/*.env.example`): `DATABASE_URL=postgres://giro_app:<senha>@<host>:5432/giro`, `DATABASE_URL_MIGRACAO=postgres://giro_migracao:<senha>@<host>:5432/giro`, `REDIS_URL=redis://:<senha>@<host>:6379/0`, `CELERY_BROKER_URL` (banco 1) e `CELERY_RESULT_BACKEND` (banco 2) no mesmo formato. Com TLS, `rediss://`. Senhas geradas por ambiente, nunca as de dev.
- **Lado do serviço:** o Postgres gerenciado exige senha por padrão (`scram-sha-256`); o Redis tem de subir com `requirepass` (ou ACL com usuário). No teste de subida: `redis-server --requirepass`, e a conferência de que o Redis responde `NOAUTH` sem senha e o Postgres recusa `giro_app` sem senha.
- **Teste de subida** (`infra/scripts/teste-subida-producao.sh`): além do que já conferia, o serviço do compose usa as URLs com senha, o Redis e o Postgres recusam quem não manda a senha, e a imagem `producao` recusa `DATABASE_URL`, `REDIS_URL` e `CELERY_BROKER_URL` sem senha, com a mensagem de `prod.py`.
- **Não coberto:** a rede em si (Postgres e Redis só alcançáveis pela rede interna do ambiente) é regra de rede do deploy, sem teste aqui; senha forte e rotação são do cofre.

## Como abrir o Admin (T-291, ADR 0029)

O Django Admin da plataforma fica em `https://admin.<domínio>/admin/` e **vem fechado**: o proxy só o atende para os IPs de um arquivo do cofre, e responde 404 (não 403) para os outros e com o arquivo vazio. Só entra quem tem `is_staff` no `public` (hoje só o Dono, criado por `createsuperuser`), sempre com 2 etapas; a sessão dura 4 horas.

1. Descubra o IP público de quem vai entrar.
2. No cofre do ambiente, edite o arquivo da lista (modelo em `infra/deploy/<ambiente>.admin-ips.conf.example`, montado no proxy como `/etc/nginx/admin-ips.conf` por `ADMIN_IPS_ARQUIVO`) e acrescente `203.0.113.10 1;` (uma linha por IP, ou faixa `203.0.113.0/24 1;`). O histórico do cofre é o registro de quem abriu e quando.
3. Recarregue o proxy sem derrubá-lo: `docker compose -f infra/deploy/docker-compose.homologacao.yml exec proxy nginx -s reload`.
4. Entre em `/admin/login/` (10 tentativas por minuto por IP; o bloqueio por tentativas e a auditoria do login são os do Django).
5. Ao terminar, **tire a linha e recarregue de novo**. Lista vazia é o estado normal.

O proxy também envia `X-Robots-Tag: noindex, nofollow` no Admin. Nos hosts das empresas, `/admin/` continua sendo a Administração da locadora, no Next. Se o servidor ficar atrás de um balanceador, o IP que o `geo` vê é o da conexão: ver o item de balanceador em "Proxy reverso". O teste de subida (`infra/scripts/teste-subida-producao.sh`) confere o 404 com a lista vazia, a tela de login com estáticos com o IP na lista, e `/admin/contratos` de uma empresa no Next. Sem VPN por ora (ADR 0029): se a equipe passar a trabalhar de IP variável, entra por ADR nova.

## Cofre do deploy depois da T-157

`prod.py` recusa subir com e-mail de desenvolvimento, SMTP sem `EMAIL_HOST`, `GIRO_ARMAZENAMENTO` diferente de `s3`, `GIRO_PROVEDOR_PAGAMENTOS` diferente de `asaas` ou `GIRO_ASAAS_CHAVE_API` vazia. O que preencher, por ambiente:

| Variável | Homologação | Produção |
| --- | --- | --- |
| `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | SMTP de teste da própria conta, com remetente `EMAIL_FROM` | SMTP de produção (porta 587 com TLS; mude `EMAIL_PORT` se o provedor for outro) |
| `GIRO_ARMAZENAMENTO` | `s3` | `s3` |
| `S3_BUCKET`, `S3_ENDPOINT_URL`, `S3_REGIAO`, `S3_CHAVE_DE_ACESSO`, `S3_CHAVE_SECRETA` | bucket próprio da homologação | bucket próprio da produção, nunca o mesmo da homologação |
| `GIRO_PROVEDOR_PAGAMENTOS` | `asaas` | `asaas` |
| `GIRO_ASAAS_URL` | `https://api-sandbox.asaas.com/v3` (já no modelo) | `https://api.asaas.com/v3` (já no modelo) |
| `GIRO_ASAAS_CHAVE_API` | chave do sandbox | chave de produção |

Os dois modelos (`infra/deploy/*.env.example`) já listavam essas variáveis desde a T-157; a T-258 acrescentou o comentário do que preencher e as três do Gunicorn. O `prod.py` não confere os `S3_*`: com eles em branco o processo sobe e o erro só aparece na primeira foto (a sugestão ao backend é a mesma trava, no mesmo `prod.py`, e vai no handoff). WhatsApp continua só com o falso e entra na trava quando a integração real existir.

## Sentry sem segredos (T-270)

O backend e o worker iniciam o Sentry por `comum/sentry.py` (`opcoes_do_sentry`), com `SENTRY_DSN_BACKEND` (vazio desliga): sem variáveis locais da pilha, sem corpo de requisição, sem o cabeçalho `asaas-access-token`, `Authorization` e cookies (nas rotas `/api/webhooks/`, sem cabeçalho nenhum), `creditCardToken` e afins pelo `EventScrubber` recursivo, e só o nome da tarefa nas tarefas do Celery. O rastro da pilha e a mensagem da exceção continuam, então a mensagem nunca pode carregar dado pessoal. Testes em `backend/tests/aceitacao/test_t270_sentry.py`, com um transporte de mentira. O Sentry do frontend ainda não existe; quando entrar, precisa da mesma regra (sem corpo de requisição, sem cabeçalhos) e do host do DSN em `connect-src`.

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
