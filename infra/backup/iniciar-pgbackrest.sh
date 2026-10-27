#!/bin/sh
# Cria o stanza do pgBackRest e confere o arquivamento de WAL (T-373). Roda UMA vez, logo depois
# da primeira subida do `db` e antes do primeiro backup. Até o stanza existir, o archive_command
# falha e o WAL se acumula no volume do banco: não deixe passar do mesmo dia.
# Uso: sh infra/backup/iniciar-pgbackrest.sh
set -eu
. "$(dirname "$0")/comum.sh"

$COMPOSE exec -T -u postgres db pgbackrest stanza-create
$COMPOSE exec -T -u postgres db psql -U "$(valor_infra POSTGRES_USER)" -d "$(valor_infra POSTGRES_DB)" -c "SELECT pg_switch_wal()"
$COMPOSE exec -T -u postgres db pgbackrest check
registrar "stanza giro criado e arquivamento de WAL conferido"
