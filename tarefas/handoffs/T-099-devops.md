# T-099 · Frontend do compose cai e não volta · devops → orquestrador

**O que foi feito:** `restart: unless-stopped` em todos os serviços do `docker-compose.yml` (db, redis, backend, worker, beat pela âncora `x-backend`, frontend). Seção "Containers parados no dev (T-099)" em `infra/README.md`. Linha em `em-andamento.md`.

**Investigação (só leitura dos containers do projeto `giro`; nada parado nem recriado):**
- Não foi queda: `OOMKilled=false`, `ExitCode=0`, nenhum erro do Next antes do SIGTERM.
- Em 09/10 os seis containers pararam entre 12:12:27Z e 12:12:31Z, na ordem inversa das dependências (frontend, beat, backend/worker, depois db e redis; db e redis com 0, worker com 137). É o padrão de `docker compose stop`/`down` no projeto.
- Docker Desktop (início 08/10 10:57) e Windows (boot 08/10 10:49) não reiniciaram; sem evento de desligamento no log do sistema.
- Backend, worker e beat foram criados em 09/10 08:24, sinal de um `up` no mesmo projeto.
- **Quem mandou o SIGTERM não dá para provar**; os containers não guardam o ator. Hipótese: o Compose nomeia o projeto pela pasta, então `make up/down/check` em qualquer pasta chamada `giro` (cópia principal ou o worktree do orquestrador) age nos mesmos containers. Para pegar em flagrante: `docker events --filter container=giro-frontend-1`.
- O caso de 08/10 à noite não foi investigado: o log antigo não está mais disponível.

**Limite da correção:** `unless-stopped` cobre queda do processo e reinício do Docker; **não** religa container parado de propósito. Por isso a nota recomenda `COMPOSE_PROJECT_NAME` e portas próprias para quem testa, e `docker compose -p giro start` para voltar sem recriar. Não mudei o nome do projeto no compose (fixar `name: giro` pioraria a colisão).

**Check:** `docker compose -p giro-t099 config` com `.env` temporário (já removido): válido, 7 serviços com a política; `infra/scripts/check-env.sh` ok. Não subi nem recriei nada; o efeito da política só vale no próximo `up` do `giro`, que é seu.

**Próximo passo:** ao recriar o compose `giro`, `docker compose up -d` aplica a política (recria os containers). O mesmo pedido de nota para os agentes (teste com outro `-p`) cabe em `docs/agentes/`, que é seu.
