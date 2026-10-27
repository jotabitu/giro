# T-373 · Produção na opção B, parte que não depende da conta · devops → orquestrador, backend, seguranca, arquiteto

**O que foi feito** (base: `origin/main` 626d432; a ADR 0033 está na branch `t-357-adr-hospedagem`, PR #394):

- **Compose de produção** `infra/deploy/docker-compose.producao.yml`: `db` (Postgres 16 com pgBackRest, imagem `infra/docker/postgres.Dockerfile`), `redis` (senha e AOF), `estaticos`, `migrar`, `backend`, `worker` (fila `celery`), **`worker-apagamento`** (só a fila `apagamento`, único serviço de execução com `DATABASE_URL_MIGRACAO`), `beat`, `frontend` (imagem nova `infra/docker/frontend.producao.Dockerfile`, Next standalone sem root) e `proxy`. Só o `proxy` publica porta (80 e 443); Postgres, Redis, backend e Next não têm `ports:`. Sub-rede fixa 172.30.0.0/24, que é o `GIRO_REDES_PROXY`. Limites de memória, rotação de log e `${VAR:?}` nas variáveis obrigatórias. Perfis `certificado` e `backup`.
- **Dois arquivos de segredos:** `producao.env` (aplicação) e o novo modelo `producao-infra.env.example` (banco, Redis, backup, DNS, alerta). A aplicação não recebe a credencial de backup nem a do DNS (ADR 0033, item 6).
- **Backup:** pgBackRest com cifra AES-256, para bucket de outro provedor, **30 dias** (`infra/backup/backup-banco.sh`: completo no domingo, diferencial nos outros dias, WAL contínuo; `iniciar-pgbackrest.sh` cria o stanza). Arquivos: rclone espelha o bucket num volume e restic guarda cifrado, 30 dias (`backup-arquivos.sh`). Timers do systemd gerados por `infra/backup/systemd/instalar.sh`.
- **Restauração testada:** `infra/backup/restaurar-teste.sh` (banco até o último WAL ou até o minuto, `migrate_schemas` do backend contra o restaurado, amostra de 5 arquivos do restic, rede e volumes descartáveis, a instância restaurada sobe com `archive_mode=off` para não escrever no repositório da produção) e `infra/backup/registro-restauracoes.md` (modelo e tabela, ainda vazia).
- **Certificado curinga:** `infra/deploy/certificado.sh emitir|renovar`, certbot DNS-01 na Cloudflare (token só de DNS), nginx recarregado se renovou.
- **Monitoramento:** `infra/monitoramento/verificar.sh` (modo rápido a cada 5 min, completo de hora em hora): serviços parados, Postgres (`pg_isready`, conexões, falha do arquivamento de WAL, idade de transação), disco a partir de 80% (crítico 90%), memória, certificado a menos de 21 dias, backups com mais de 26 horas; e-mail por SMTP, um aviso a cada 6 horas por problema e aviso de resolvido; batimento opcional (Healthchecks.io).
- **Cofre:** `infra/deploy/baixar-segredos.sh` (Doppler ou Bitwarden Secrets Manager) grava `/etc/giro/*` com permissão 600.
- **CI:** `infra/scripts/check-producao.sh` no job Infra: `docker compose config` da produção com valores de teste e `check-producao.mjs` (só o proxy publica 80 e 443; `DATABASE_URL_MIGRACAO` só no `migrar` e no `worker-apagamento`; worker do apagamento só na fila `apagamento`; nenhum segredo de infra na aplicação; pgBackRest cifrado e com 30 dias; Redis com senha). Testei também com um JSON proposital errado: acusa 9 violações.
- **Roteiro:** `infra/README.md`, seção "Produção (ADR 0033, opção B)": o que sobe, o que o dono contrata, os segredos do cofre, 11 passos de subida e a operação. A tabela do início do README trocou "a definir em ADR".

**Onde:** `infra/deploy/` (compose, `producao-infra.env.example`, `certificado.sh`, `baixar-segredos.sh`, `producao.env.example`), `infra/docker/` (`postgres.Dockerfile`, `frontend.producao.Dockerfile`), `infra/backup/`, `infra/monitoramento/`, `infra/scripts/check-producao.*`, `.github/workflows/ci.yml`, `infra/README.md`.

**O que testei de verdade (sem conta):**
- `check-producao.sh` passa aqui (Compose v5.6); roda no CI.
- **Fluxo do pgBackRest, com repositório local no lugar do S3 e a mesma cifra e as mesmas variáveis:** subir o Postgres com o `archive_command`, `stanza-create`, `check`, backup completo, backup diferencial, `restore` num volume novo, subir o restaurado com `archive_mode=off` e ler os dados: voltaram as duas linhas, inclusive a do WAL posterior ao completo. Isso achou dois erros que já estão corrigidos no compose: (1) **`init: true` no `db` é obrigatório**: com `PGBACKREST_ARCHIVE_ASYNC=y` o pgBackRest deixa um processo órfão que o Postgres, como processo 1, trata como queda e reinicia o servidor em laço; (2) sem `PGBACKREST_PG1_USER` e `PGBACKREST_PG1_DATABASE` o pgBackRest procura o papel `postgres`, que não existe (o superusuário é `giro`).
- A imagem `frontend.producao.Dockerfile` constrói e sobe (usuário sem root, HTTP 200). Achei que o build exige `npm run api:gerar` antes (o cliente tipado não está no git); o Dockerfile já faz isso.
- `postgres.Dockerfile` constrói (pgBackRest 2.59.3), e conferi que as opções usadas existem nessa versão.
- `sh -n` em todos os scripts.

**O que NÃO foi testado (só dá para fazer depois da conta):**
1. O repositório pgBackRest e o restic **em S3 de verdade** (B2 ou R2: endpoint, região, `uri-style path`, Object Lock), o rclone lendo o bucket do provedor da VPS, e o tempo do primeiro backup.
2. `docker compose up` completo com segredos reais (build do backend de produção, `migrar`, Gunicorn, proxy com o certificado).
3. `certificado.sh emitir` (DNS-01 na Cloudflare e a propagação) e a renovação.
4. `restaurar-teste.sh` inteiro (a parte do banco foi testada à mão em separado; as conferências do `migrate_schemas` e do restic não rodaram) e o passo manual da foto pela URL assinada. **A primeira linha do registro só existe depois disso.**
5. `verificar.sh` (e-mail por SMTP, leitura do JSON do pgBackRest e do restic, `openssl` contra o proxy), `instalar.sh` e os timers, e `baixar-segredos.sh` com Doppler ou Bitwarden.
6. O teste de fora (só 80 e 443 respondem) e os limites de memória no tamanho real da VPS.

**Pendências para outros agentes, com bloqueio:**
- **BLOQUEIA o apagamento (backend):** o worker próprio só lê a fila `apagamento`, mas o backend **não roteia** a tarefa para ela: `CELERY_TASK_ROUTES = {"aud_08_apagar_empresas": {"queue": "apagamento"}}` em `config/settings/base.py` (o `beat` usa o nome da tarefa, então a rota vale para ele) e um teste de que a tarefa tem essa rota. Sem isso, na produção a tarefa cai na fila `celery`, que o worker comum lê **sem** credencial, e o apagamento (AUD-08) falha no `DROP SCHEMA`. Peço a tarefa ao Orquestrador. O desenho é o do M-01 da T-355 (fila só da `aud_08_apagar_empresas`).
- **Backend:** não achei comando que crie o primeiro dono da plataforma em produção (o `seed_moto_rapida` não roda com `prod.py`). O roteiro anota a pendência no passo 11.
- **Arquiteto:** a memória soma 7,5 GB de limites para uma VPS de 8 GB (backend 3 GB, banco 2 GB, workers 1,5 GB, Redis 0,4 GB, Next 0,5 GB, proxy 0,1 GB). Cabe porque o limite é teto e não reserva, mas sem folga para o espelho do restic nem para leitura simultânea de CRLV-e. Rever o tamanho da VPS ou os limites depois de medir (`docker stats`) com tráfego real. O espelho do restic também pede disco igual ao bucket de arquivos.
- **Segurança:** o restic precisa de uma chave só de leitura para o bucket de arquivos (`ARQUIVOS_S3_CHAVE_LEITURA`); conferir que o provedor permite essa política.
- **Sem ADR nova:** pgBackRest, restic, rclone, certbot e `tini` (`init: true`) são as peças que a ADR 0033 já nomeia, e não trocam banco, fila nem nuvem.

**Conflitos esperados no merge:** a T-352 (PR #389) e a T-361 (PR #397) também mexem em `infra/README.md` (T-361 no fim do arquivo; a T-352 na seção "Papéis de banco"), em `.github/workflows/ci.yml` (T-352, job Infra) e em `tarefas/feito.md`. Em `feito.md` mantenha as linhas dos dois lados. O compose de produção já usa o desenho da T-352 (a credencial zerada nos serviços web e `beat`), mas não depende dela. Quando os dois entrarem, o `check-migracao-so-no-worker.sh` da T-352 continua valendo só para o dev e a homologação.

**Próximo passo para quem recebe:** (orquestrador) abrir o PR; pedir ao backend a rota da fila `apagamento`; contratar a conta com o dono seguindo o roteiro; depois da conta, o devops faz a "Subida de produção" (passos 1 a 10 do README) e registra a primeira restauração.
