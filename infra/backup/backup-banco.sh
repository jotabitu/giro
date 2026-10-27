#!/bin/sh
# Backup do banco pelo pgBackRest (T-373, ADR 0033): completo aos domingos, diferencial nos outros
# dias, e o WAL é arquivado o tempo todo pelo archive_command. A retenção de 30 dias e a cifra
# AES-256 vêm do ambiente do `db` (docker-compose.producao.yml); o `expire` roda no fim do backup.
# Uso: sh infra/backup/backup-banco.sh full|diff
set -eu
. "$(dirname "$0")/comum.sh"

tipo=${1:?uso: backup-banco.sh full|diff}
case "$tipo" in full | diff) ;; *) echo "tipo deve ser full ou diff"; exit 2 ;; esac

inicio=$(date +%s)
$COMPOSE exec -T -u postgres db pgbackrest --type="$tipo" backup
registrar "backup do banco ($tipo) concluído em $(( $(date +%s) - inicio )) s"
