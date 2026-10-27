#!/bin/sh
# Falha se a DATABASE_URL_MIGRACAO chegar a quem não deve (T-352, T-382): é credencial com DDL em
# todos os schemas, e só a aud_08_apagar_empresas usa. Ela vai ao worker que lê a fila `apagamento`
# (para onde o backend manda a tarefa, CELERY_TASK_ROUTES) e a mais ninguém: nem ao backend (web),
# nem ao beat, nem a outro worker; e nenhum outro serviço lê essa fila.
#   desenvolvimento: um worker só, que lê `celery` e `apagamento` e recebe a credencial
#   homologação:     `worker` (só `celery`, sem a credencial) e `worker-apagamento` (só `apagamento`)
# Confere o compose de desenvolvimento (com o .env.example) e o de homologação (com o modelo dele).
set -e
cd "$(dirname "$0")/../.."

command -v jq >/dev/null || { echo "jq não encontrado"; exit 1; }

# conferir <json> <rótulo> <serviço que recebe a credencial e lê a fila apagamento>
conferir() {
  json=$1
  rotulo=$2
  com=$3
  for servico in $(echo "$json" | jq -r '.services | keys[]'); do
    valor=$(echo "$json" | jq -r --arg s "$servico" '.services[$s].environment.DATABASE_URL_MIGRACAO // ""')
    le_fila=$(echo "$json" | jq -r --arg s "$servico" '(.services[$s].command // []) | join(" ") | contains("apagamento")')
    if [ "$servico" = "$com" ]; then
      [ -n "$valor" ] || { echo "$rotulo: $com não recebe a DATABASE_URL_MIGRACAO."; exit 1; }
      [ "$le_fila" = true ] || { echo "$rotulo: $com não lê a fila apagamento."; exit 1; }
    else
      # `migrar` (homologação) recebe a credencial para o migrate_schemas e sai; não é worker.
      [ "$servico" = migrar ] || [ -z "$valor" ] || { echo "$rotulo: $servico recebe a DATABASE_URL_MIGRACAO; só $com pode."; exit 1; }
      [ "$le_fila" = false ] || { echo "$rotulo: $servico lê a fila apagamento; só $com pode."; exit 1; }
    fi
  done
}

# Desenvolvimento: o valor vem do .env, que o worker lê por env_file.
cp .env.example .env
conferir "$(docker compose config --format json)" "docker-compose.yml" worker

# Homologação: o modelo traz o valor vazio, então o check usa um valor de teste na interpolação.
DATABASE_URL_MIGRACAO=postgres://giro_migracao:so-para-o-check@db:5432/giro \
  ENV_FILE=homologacao.env.example DOMINIO_BASE=exemplo.test FRONTEND_UPSTREAM=frontend:3000 \
  ADMIN_IPS_ARQUIVO=./homologacao.admin-ips.conf.example CERT_DIR_HOST=. \
  docker compose -f infra/deploy/docker-compose.homologacao.yml config --format json > /tmp/homologacao.json
conferir "$(cat /tmp/homologacao.json)" "docker-compose.homologacao.yml" worker-apagamento

echo "DATABASE_URL_MIGRACAO só no worker que lê a fila apagamento"
