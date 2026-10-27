# T-352 · DATABASE_URL_MIGRACAO só no worker · devops → orquestrador, seguranca

**O que foi feito:** a `DATABASE_URL_MIGRACAO` (credencial com DDL em todos os schemas) passou a chegar só ao `worker` do Celery, que roda a `plataforma.aud_08_apagar_empresas`. O `backend` (web) e o `beat` não a recebem (B-01 da T-199, T-345).

- **Como:** o arquivo de variáveis é o mesmo para todos os serviços (`env_file`), então não basta omitir a variável no web. O compose a zera com `environment: DATABASE_URL_MIGRACAO: ""` no `backend` e no `beat` (`environment` vence o `env_file`); o `worker` a lê do `.env` em desenvolvimento.
- **Homologação:** o `worker` passa a recebê-la de forma explícita (`DATABASE_URL_MIGRACAO: ${DATABASE_URL_MIGRACAO}`, do cofre, como o `migrar`). Zerada no `backend`, no `beat` e no `estaticos`. O `migrar` segue com ela para o `migrate_schemas`.
- **Produção:** não há compose de produção no repositório; o `producao.env.example` ganhou o mesmo comentário (worker e `migrar`, não o web nem o beat). Quem escrever o compose de produção deve repetir o desenho da homologação.
- **Conferência no código:** no backend, só `apps/plataforma/banco.py` (`apagar_schema`, chamada pela tarefa) lê a variável em execução; o entrypoint migra com `DATABASE_URL`. Então o web não perde nada ao deixá-la vazia. Vazia, o backend não falha: cai no log de erro da T-345.
- **CI:** novo `infra/scripts/check-migracao-so-no-worker.sh`, no job Infra do `ci.yml`: falha se `backend` ou `beat` receber a variável, ou se o `worker` não a receber, no compose de desenvolvimento (com o `.env.example`) e no de homologação (com o modelo e valores de teste).

**Onde:** `docker-compose.yml`, `infra/deploy/docker-compose.homologacao.yml`, `.env.example`, `infra/deploy/homologacao.env.example`, `infra/deploy/producao.env.example`, `infra/README.md` (seção "Papéis de banco"), `infra/scripts/check-migracao-so-no-worker.sh`, `.github/workflows/ci.yml`.

**Testes:** `docker compose config` da homologação com o modelo: `backend`, `beat`, `estaticos` e `migrar` com a variável vazia, `worker` com o valor. A parte de desenvolvimento do script **não rodou aqui**: a máquina não tem `jq` e uma regra de permissão bloqueou `cp .env.example .env`; ela roda no CI (mesmo `cp` do passo vizinho). O YAML do `docker-compose.yml` não foi validado por `docker compose config` pelo mesmo motivo.

**Não mexi:** pilha `giro`, `giro-backend-pg`, telas de Veículos.

**Próximo passo para quem recebe:** (orquestrador) abrir o PR e conferir o job Infra no CI antes do merge; se a parte de desenvolvimento do script falhar lá, o ajuste é no script. (segurança) B-01 atendido; fechar o achado.
