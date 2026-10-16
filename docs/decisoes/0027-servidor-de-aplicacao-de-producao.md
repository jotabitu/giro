# Servidor de aplicação de homologação e produção

**Status:** aceita · 15 out 2026 · T-264 (achado do devops na T-258) · detalha a 0026 (tempo da leitura de PDF)

## Contexto

A imagem do backend (`infra/docker/backend.Dockerfile`) termina em `CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]`, e o `docker-compose.yml` repete o mesmo comando. O `runserver` é o servidor de desenvolvimento do Django: a própria documentação diz para não usá-lo em produção (não passou por revisão de segurança nem de desempenho, recarrega código, um processo só). A imagem também instala o `requirements-dev.txt` (pytest, ruff, mypy) e roda como root.

Na T-258 o devops escreveu `infra/docker/gunicorn.conf.py` para a leitura do CRLV-e e da CNH-e (ADR 0026), que segura a requisição por até 8 s esperando um processo filho, e as variáveis `GUNICORN_*` em `infra/deploy/*.env.example`. O `gunicorn` não está em `requirements.txt` e nenhuma imagem usa esse arquivo. Nenhuma homologação sobe assim.

O que pesa na escolha:

- O backend é Django síncrono: views do DRF, ORM e django-tenants (o schema é escolhido por conexão, por requisição). Não há view assíncrona, WebSocket nem streaming; trabalho demorado vai para o Celery (ADR 0012).
- A exceção é a leitura de PDF: até 8 s parada esperando o filho, sem CPU no processo do Django.
- O Django só é alcançável pelo proxy (`infra/proxy/giro.conf.template`), que já corta a requisição lenta (20 s na rota de leitura, 60 s no resto), limita corpo e taxa e termina o TLS.

## Decisão

### 1. Gunicorn, WSGI, com o `gunicorn.conf.py` da T-258

- Homologação e produção sobem com `gunicorn -c /app/gunicorn.conf.py config.wsgi:application`. O arquivo de configuração é o `infra/docker/gunicorn.conf.py`, sem mudança de valores.
- **Por que Gunicorn:** é o servidor WSGI mais usado com Django, tem a documentação de deploy do próprio Django, configuração em Python (o arquivo já existe e foi conferido com `--check-config`), mestre que repõe worker morto e recicla por `max_requests`, e é Python puro (não pede compilação na imagem).
- **Alternativas descartadas:** uWSGI (em modo de manutenção desde 2022, configuração extensa, compila C); Uvicorn ou Daphne com ASGI (não há código assíncrono para ganhar, e o ORM síncrono sob ASGI roda em thread de qualquer forma, com uma camada a mais e a conexão do django-tenants por thread a conferir); Waitress (menos usado com Django, sem reciclagem de worker). Trocar de servidor depois é barato (muda a imagem, não o código), mas pede ADR nova.

### 2. Workers, threads e tempos

| Item | Valor | Por quê |
| --- | --- | --- |
| Classe de worker | `gthread` | A leitura de PDF espera o filho até 8 s; com `sync`, cada leitura prende um worker inteiro. Com threads, as outras requisições seguem no mesmo worker. O ORM do Django abre uma conexão por thread; o django-tenants troca o schema na conexão da thread da requisição. |
| Workers × threads | homologação 2 × 4; produção 3 × 4 (`GUNICORN_WORKERS`, `GUNICORN_THREADS`) | Memória: 250 a 300 MiB por worker mais os filhos da leitura cabem em 2 GiB e 4 GiB (tabela em `infra/README.md`, "Servidor da aplicação e leitura de PDF"). Não seguimos a fórmula `2 × núcleos + 1` porque o limite aqui é memória, não CPU. |
| Conexões no Postgres | até workers × threads por contêiner do backend (12 em produção), mais o Celery | `CONN_MAX_AGE` fica como está; quem aumentar workers ou threads confere `max_connections` do Postgres. |
| `timeout` | 30 s (`GUNICORN_TIMEOUT`) | No `gthread` ele não corta requisição lenta, só mata o worker que parou de avisar o mestre. Fica 3,75 vezes acima dos 8 s da leitura para continuar valendo se a classe virar `sync`. |
| Corte por requisição | o proxy: 20 s na leitura, 60 s no resto | O Gunicorn não tem limite por rota. Nenhum timeout novo no Django. |
| `graceful_timeout` | 30 s | No deploy, a requisição em curso termina antes de o worker sair; acima dos 20 s da leitura. |
| `keepalive` | 5 s | O proxy fala com o Gunicorn na rede interna. |
| `max_requests` / `jitter` | 1000 / 100 | Recicla o worker aos poucos e limita vazamento de memória; o jitter evita reiniciar todos juntos. |
| `worker_tmp_dir` | `/dev/shm` | O heartbeat do worker não trava em disco lento de contêiner. |
| Logs | erro na saída padrão; sem log de acesso | O proxy registra o acesso; o Sentry pega as exceções. Nada de corpo nem de cabeçalho em log (ADR 0026). |

O cabeçalho `X-Forwarded-Proto` continua lido pelo Django (`SECURE_PROXY_SSL_HEADER` em `prod.py`) e não pelo Gunicorn: o `forwarded_allow_ips` fica no padrão, e o backend só recebe tráfego do proxy (regra de rede de `infra/README.md`).

### 3. `runserver` só no desenvolvimento

- O `backend.Dockerfile` ganha dois alvos (`--target`) na mesma base de sistema:
  - `dev`: instala `requirements-dev.txt`, roda como hoje e é o alvo do `docker-compose.yml`, que segue com `runserver` e bind mount (recarrega ao editar).
  - `producao`: instala só `requirements.txt`, copia o código e o `gunicorn.conf.py` para `/app`, roda com um usuário sem root e termina em `CMD ["gunicorn", "-c", "/app/gunicorn.conf.py", "config.wsgi:application"]`. É o alvo de homologação e produção; o worker e o beat do Celery usam a mesma imagem com o comando deles.
- O `CMD` da imagem de produção nunca é `runserver`. O `prod.py` não precisa recusar o `runserver`: a imagem de produção não tem o comando de desenvolvimento como padrão, e o compose de homologação não o sobrescreve.
- As migrações continuam no `backend-entrypoint.sh` com `RODAR_MIGRACOES=1` em um único serviço por ambiente, antes de o Gunicorn subir (o `exec "$@"` já faz o Gunicorn ser o processo 1 e receber o `SIGTERM` do deploy).

### 4. Dependência nova

`gunicorn>=23,<24` em `backend/requirements.txt` (não no `-dev`), registrada no PR do devops: servidor WSGI de homologação e produção, esta ADR. A 23 é a linha com as correções de *request smuggling* das versões anteriores. Sem outra dependência: nada de `uvicorn`, `gevent` ou `whitenoise` nesta decisão.

## Consequências

- A homologação pode subir com um servidor de produção; o `runserver` deixa de existir fora do desenvolvimento.
- A imagem de produção fica menor e sem ferramentas de teste, e não roda como root.
- Mudar workers, threads ou o timeout é variável de ambiente, sem nova imagem; mudar a classe de worker ou o servidor pede ADR nova.
- A tabela de memória da T-258 é estimativa. Quando o parser da leitura existir (T-265, com o semáforo de leituras simultâneas), o devops mede o pico real e revê workers e threads no `infra/README.md`.
- Fica de fora desta ADR: arquivos estáticos do Admin da plataforma (o proxy manda `/` para o Next; o devops decide se o proxy serve `STATIC_ROOT` depois de um `collectstatic` no build, sem dependência nova) e a rota de saúde para o orquestrador de contêineres (não existe hoje; o teste de subida chama uma rota da API pelo proxy, e um 401 sem login já prova que o Django respondeu).

## Pronto quando (devops)

- `backend.Dockerfile` com os alvos `dev` e `producao` como no item 3; `docker-compose.yml` com `target: dev`; compose de homologação com `target: producao` e as variáveis `GUNICORN_*`.
- `gunicorn` em `requirements.txt` com o motivo no PR.
- Teste de subida: a imagem `producao` sobe com `config.settings.prod` e as variáveis de `homologacao.env.example`, o processo 1 é o Gunicorn com 2 workers `gthread`, uma requisição pela rota do proxy responde, e `docker stop` encerra sem matar a requisição em curso.
- `infra/README.md`, seção "Servidor da aplicação e leitura de PDF", sem o aviso "Ainda não há imagem de produção".
