# T-382 · Rota da tarefa de apagamento para a fila própria · devops → orquestrador, backend, qa

**O que foi feito** (branch a partir da `origin/t-352-database-url-migracao`, PR #389; só entra depois dele):

- **Rota:** `CELERY_TASK_ROUTES = {"aud_08_apagar_empresas": {"queue": "apagamento"}}` em `backend/config/settings/base.py`. O Beat usa o nome da tarefa e a rota decide a fila. Nada em `comum/worker.py`.
- **Dev (`docker-compose.yml`):** o único `worker` passa a ler `-Q celery,apagamento` (e continua com a `DATABASE_URL_MIGRACAO` do `.env`); sem isso a tarefa ficaria parada na fila nova.
- **Homologação:** passa a ter o mesmo desenho da produção (T-373): `worker` só na fila `celery`, sem a credencial, e `worker-apagamento` só na fila `apagamento` (`--concurrency=1`), com a credencial do cofre. Isso desfaz, na homologação, o "worker único com a credencial" da T-352: era o desenho certo antes de existir a fila.
- **Produção:** o `docker-compose.producao.yml` (T-373, PR #399) já tem os dois workers; nada a mudar nele. Quando o #399 entrar, o `check-producao.mjs` dele continua valendo.
- **Check:** `check-migracao-so-no-worker.sh` agora exige que a credencial esteja só no worker que lê a fila `apagamento` (`worker` no dev, `worker-apagamento` na homologação) e que nenhum outro serviço leia essa fila. `infra/README.md` ajustado.
- **Testes** (`backend/tests/aceitacao/test_t382_rota_apagamento.py`, 3 testes): `test_aud_08_apagar_empresas_vai_para_a_fila_apagamento` (`app.amqp.router.route`), `test_aud_08_outras_tarefas_ficam_na_fila_padrao` e `test_aud_08_agenda_nao_fixa_fila_por_fora_da_rota`.

**Conferência:** `ruff check`, `ruff format --check` e `mypy` nos dois arquivos, e os 3 testes: passaram, num `docker run` avulso na rede `giro-backend-teste`, só esses arquivos (o `t196-plataforma` do Backend estava numa rodada; meus testes não tocam o banco). Não rodei a suíte inteira: com `CELERY_TASK_ALWAYS_EAGER` a rota não muda o que os testes de `aud_08_*` fazem. `docker compose config` da homologação: `worker-apagamento` com a credencial e lendo `apagamento`; `worker`, `backend`, `beat` e `estaticos` sem a credencial e sem ler a fila. **Não rodei** o `check-migracao-so-no-worker.sh` inteiro aqui (sem `jq`, e uma regra bloqueia `cp .env.example .env`): roda no CI. O worker dev com `-Q celery,apagamento` não foi subido.

**Para o CI conferir:** o job Infra deve rodar o `check-migracao-so-no-worker.sh` verde nos dois compose.

**Próximo passo para quem recebe:** (orquestrador) abrir o PR depois do #389; (backend) nada; a pendência da T-373 sobre a rota está atendida por esta tarefa.
