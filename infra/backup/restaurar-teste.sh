#!/bin/sh
# Restauração testada (T-373, ADR 0033, item 3): antes do primeiro cliente e uma vez por mês.
# Restaura o backup mais recente do banco (pgBackRest) e uma amostra dos arquivos (restic) numa
# rede e em volumes descartáveis, e confere o que dá para conferir por script. A restauração
# NUNCA toca o banco de produção: a instância restaurada sobe com archive_mode=off (senão ela
# enviaria WAL ao repositório da produção) e sem porta publicada.
#
# Uso: sh infra/backup/restaurar-teste.sh           (até o último WAL arquivado)
#      sh infra/backup/restaurar-teste.sh "2026-11-02 14:30:00-03"   (recuperação até o minuto)
# Roda na VPS ou numa máquina de teste com Docker e os arquivos de segredos (GIRO_SEGREDOS).
# Depois: preencha uma linha em infra/backup/registro-restauracoes.md, com o passo manual da foto.
set -eu
. "$(dirname "$0")/comum.sh"

ALVO=${1:-}
REDE=giro-restauracao
VOLUME=giro_restauracao_pgdata
BANCO=giro-restauracao-db
FALHAS=0
INICIO=$(date +%s)
INFRA_ENV="$SEGREDOS/producao-infra.env"
USUARIO=$(valor_infra POSTGRES_USER)
NOMEBANCO=$(valor_infra POSTGRES_DB)
SENHA_MIGRACAO=$(valor_infra POSTGRES_PASSWORD_MIGRACAO)

limpar() {
  docker rm -f "$BANCO" >/dev/null 2>&1 || true
  docker volume rm "$VOLUME" >/dev/null 2>&1 || true
  docker volume rm giro_restauracao_arquivos >/dev/null 2>&1 || true
  docker network rm "$REDE" >/dev/null 2>&1 || true
}
trap limpar EXIT
limpar
docker network create "$REDE" >/dev/null

confere() { # descrição, comando
  if sh -c "$2" >/dev/null 2>&1; then registrar "ok    $1"; else registrar "FALHA $1"; FALHAS=$((FALHAS + 1)); fi
}

IMAGEM_BANCO=giro-postgres:producao
docker image inspect "$IMAGEM_BANCO" >/dev/null 2>&1 || $COMPOSE build db

# 1. Restaura o banco. `--delta` não é preciso: o volume é novo.
registrar "restaurando o banco${ALVO:+ até $ALVO}"
if [ -n "$ALVO" ]; then
  TIPO="--type=time --target=$ALVO --target-action=promote"
else
  TIPO="--type=default"
fi
# shellcheck disable=SC2086
docker run --rm --user postgres --env-file "$INFRA_ENV" -e PGBACKREST_STANZA=giro \
  -e PGBACKREST_PG1_PATH=/var/lib/postgresql/data -e PGBACKREST_REPO1_TYPE=s3 \
  -e PGBACKREST_REPO1_S3_URI_STYLE=path -e PGBACKREST_REPO1_PATH=/giro \
  -e PGBACKREST_REPO1_CIPHER_TYPE=aes-256-cbc \
  -v "$VOLUME":/var/lib/postgresql/data --entrypoint pgbackrest "$IMAGEM_BANCO" \
  --stanza=giro $TIPO restore

# 2. Sobe a instância restaurada, isolada (sem arquivamento, sem porta).
docker run -d --init --name "$BANCO" --network "$REDE" --user postgres --env-file "$INFRA_ENV" \
  -e PGBACKREST_STANZA=giro -e PGBACKREST_PG1_PATH=/var/lib/postgresql/data \
  -e PGBACKREST_REPO1_TYPE=s3 -e PGBACKREST_REPO1_S3_URI_STYLE=path -e PGBACKREST_REPO1_PATH=/giro \
  -e PGBACKREST_REPO1_CIPHER_TYPE=aes-256-cbc \
  -v "$VOLUME":/var/lib/postgresql/data --entrypoint postgres "$IMAGEM_BANCO" \
  -c archive_mode=off -c archive_command=/bin/true -c listen_addresses='*' >/dev/null
tentativas=0
until docker exec "$BANCO" pg_isready -U "$USUARIO" -d "$NOMEBANCO" >/dev/null 2>&1; do
  tentativas=$((tentativas + 1))
  [ "$tentativas" -gt 120 ] && { registrar "FALHA o banco restaurado não aceitou conexão em 2 minutos"; exit 1; }
  sleep 1
done
registrar "banco restaurado no ar"

psql_restaurado() { docker exec "$BANCO" psql -U "$USUARIO" -d "$NOMEBANCO" -tAc "$1"; }

# 3. Conferências do banco.
confere "há tabelas de migração do Django" "[ \"\$(docker exec $BANCO psql -U $USUARIO -d $NOMEBANCO -tAc 'SELECT count(*) FROM django_migrations')\" -gt 0 ]"
confere "o schema da plataforma (public) tem empresas" "[ \"\$(docker exec $BANCO psql -U $USUARIO -d $NOMEBANCO -tAc \"SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE 'plataforma_empresa%'\")\" -gt 0 ]"
registrar "schemas de empresa restaurados: $(psql_restaurado "SELECT count(*) FROM pg_namespace WHERE nspname NOT LIKE 'pg\_%' AND nspname NOT IN ('information_schema','public')")"

# O backend de produção contra o banco restaurado: `migrate_schemas` não pode ter nada a aplicar.
SAIDA=$(mktemp)
for escopo in --shared --tenant; do
  docker run --rm --network "$REDE" --env-file "$ENV_FILE" \
    -e DATABASE_URL="postgres://giro_migracao:$SENHA_MIGRACAO@$BANCO:5432/$NOMEBANCO" \
    -e DATABASE_URL_MIGRACAO="postgres://giro_migracao:$SENHA_MIGRACAO@$BANCO:5432/$NOMEBANCO" \
    --entrypoint python giro-backend:producao manage.py migrate_schemas "$escopo" --noinput >>"$SAIDA" 2>&1 || FALHAS=$((FALHAS + 1))
done
confere "migrate_schemas não aplicou nada no banco restaurado" "! grep -q 'Applying ' $SAIDA"
rm -f "$SAIDA"

# 4. Amostra dos arquivos: restaura 5 arquivos do último snapshot e confere que não estão vazios.
registrar "restaurando uma amostra dos arquivos"
docker volume create giro_restauracao_arquivos >/dev/null
docker run --rm --env-file "$INFRA_ENV" -e RESTIC_CACHE_DIR=/tmp/cache \
  -v giro_restauracao_arquivos:/restaurado --entrypoint sh restic/restic:0.17.3 -c '
    set -e
    amostra=$(restic ls latest --tag arquivos 2>/dev/null | grep -E "\.(jpg|jpeg|png|pdf)$" | awk "NR % 7 == 1" | head -n 5)
    [ -n "$amostra" ] || { echo "snapshot sem arquivos de imagem ou PDF"; exit 1; }
    for f in $amostra; do restic restore latest --tag arquivos --target /restaurado --include "$f" >/dev/null; done
    find /restaurado -type f -size +0 | head -n 5 | wc -l | grep -qv "^0$"
  ' && registrar "ok    amostra de arquivos restaurada e não vazia" || { registrar "FALHA amostra de arquivos"; FALHAS=$((FALHAS + 1)); }

DURACAO=$(( $(date +%s) - INICIO ))
registrar "duração total: $((DURACAO / 60)) min $((DURACAO % 60)) s; falhas: $FALHAS"
echo
echo "Linha para infra/backup/registro-restauracoes.md (preencha quem fez e o passo manual):"
echo "| $(date +%Y-%m-%d) | <quem> | ${ALVO:-último WAL} | $((DURACAO / 60)) min | $([ "$FALHAS" -eq 0 ] && echo ok || echo "$FALHAS falha(s)") | <foto abriu pela URL assinada: sim/não> | <observações> |"
[ "$FALHAS" -eq 0 ]
