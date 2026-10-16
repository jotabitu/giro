# T-264 · Servidor de aplicação de produção (ADR) · arquiteto → devops

**O que foi feito:** ADR 0027. Homologação e produção sobem com Gunicorn (WSGI, `gthread`) e o `infra/docker/gunicorn.conf.py` da T-258 sem mudar valores; `runserver` só no compose de desenvolvimento.
**Onde:** `docs/decisoes/0027-servidor-de-aplicacao-de-producao.md`, índice em `docs/decisoes/README.md`, estado da T-264 em `tarefas/backlog.md`.
**Decisões:**
- Gunicorn no lugar de uWSGI (manutenção), Uvicorn/Daphne com ASGI (sem código assíncrono) e Waitress.
- `gthread`: 2 workers × 4 threads em homologação, 3 × 4 em produção; `timeout` 30 s (só mata worker travado), corte por requisição no proxy (20 s na leitura, 60 s no resto); `graceful_timeout` 30 s; `max_requests` 1000 com jitter 100.
- `backend.Dockerfile` com dois alvos: `dev` (requirements-dev, `runserver` pelo compose) e `producao` (só `requirements.txt`, usuário sem root, `CMD` gunicorn). Worker e beat usam a imagem `producao`.
- `X-Forwarded-Proto` continua no Django (`SECURE_PROXY_SSL_HEADER`), não no Gunicorn.
- Dependência nova: `gunicorn>=23,<24` em `requirements.txt`, com o motivo no PR do devops.
**O que ficou de fora:** estáticos do Admin da plataforma (o proxy manda `/` para o Next; o devops decide servir `STATIC_ROOT` pelo proxy) e uma rota de saúde (não existe; o teste de subida aceita o 401 de uma rota da API). A medição real de memória espera o parser da T-265.
**Próximo passo para quem recebe (devops):** o "Pronto quando" no fim da ADR: alvos do Dockerfile, `target` nos composes, `gunicorn` no `requirements.txt` e o teste de subida da imagem `producao` com as variáveis de homologação.
