#!/bin/sh
# Espera o Postgres e, só no serviço backend, aplica as migrações de todos os schemas.
set -e

until pg_isready -h "${POSTGRES_HOST:-db}" -p "${POSTGRES_PORT:-5432}" -U "${POSTGRES_USER:-giro}" >/dev/null 2>&1; do
  echo "Aguardando o Postgres em ${POSTGRES_HOST:-db}..."
  sleep 1
done

if [ "${RODAR_MIGRACOES:-0}" = "1" ]; then
  python manage.py migrate_schemas --shared --noinput
  python manage.py migrate_schemas --tenant --noinput
fi

exec "$@"
