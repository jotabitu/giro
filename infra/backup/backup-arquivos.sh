#!/bin/sh
# Backup dos arquivos (fotos de vistoria, documentos, logos) (T-373, ADR 0033): o rclone espelha o
# bucket de arquivos da aplicação num volume e o restic guarda o espelho cifrado no bucket de backup
# de outro provedor, com retenção de 30 dias. O espelho acompanha as remoções: o que a AUD-08
# apaga no 90º dia some do bucket e, em até 30 dias, do último snapshot.
# Uso: sh infra/backup/backup-arquivos.sh            (backup diário)
#      sh infra/backup/backup-arquivos.sh verificar  (confere o repositório, semanal)
set -eu
. "$(dirname "$0")/comum.sh"

restic() { $COMPOSE --profile backup run --rm restic "$@"; }

if [ "${1:-}" = verificar ]; then
  restic check --read-data-subset=5%
  registrar "repositório restic conferido (5% dos dados lidos)"
  exit 0
fi

inicio=$(date +%s)
$COMPOSE --profile backup run --rm rclone-arquivos
restic cat config >/dev/null 2>&1 || restic init
restic backup /espelho --tag arquivos --host giro-producao
# 30 dias, contados de cada snapshot (ADR 0033, item 1). Nada de cópia mensal ou anual.
restic forget --tag arquivos --keep-within 30d --prune
registrar "backup dos arquivos concluído em $(( $(date +%s) - inicio )) s"
