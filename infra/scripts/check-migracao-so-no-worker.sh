#!/bin/sh
# Falha se o backend (web) ou o beat receber a DATABASE_URL_MIGRACAO, ou se o worker não a receber
# (T-352): é credencial com DDL em todos os schemas, e só a aud_08_apagar_empresas, no worker, usa.
# Confere o compose de desenvolvimento (com o .env.example) e o de homologação (com o modelo dele).
set -e
cd "$(dirname "$0")/../.."

command -v jq >/dev/null || { echo "jq não encontrado"; exit 1; }

conferir() {
  json=$1
  rotulo=$2
  for servico in backend beat; do
    valor=$(echo "$json" | jq -r --arg s "$servico" '.services[$s].environment.DATABASE_URL_MIGRACAO // ""')
    if [ -n "$valor" ]; then
      echo "$rotulo: o serviço $servico recebe a DATABASE_URL_MIGRACAO; só o worker pode receber."
      exit 1
    fi
  done
  valor=$(echo "$json" | jq -r '.services.worker.environment.DATABASE_URL_MIGRACAO // ""')
  if [ -z "$valor" ]; then
    echo "$rotulo: o worker não recebe a DATABASE_URL_MIGRACAO."
    exit 1
  fi
}

# Desenvolvimento: o valor vem do .env, que o worker lê por env_file.
cp .env.example .env
conferir "$(docker compose config --format json)" "docker-compose.yml"

# Homologação: o modelo traz o valor vazio, então o check usa um valor de teste na interpolação.
DATABASE_URL_MIGRACAO=postgres://giro_migracao:so-para-o-check@db:5432/giro \
  ENV_FILE=homologacao.env.example DOMINIO_BASE=exemplo.test FRONTEND_UPSTREAM=frontend:3000 \
  ADMIN_IPS_ARQUIVO=./homologacao.admin-ips.conf.example CERT_DIR_HOST=. \
  docker compose -f infra/deploy/docker-compose.homologacao.yml config --format json > /tmp/homologacao.json
conferir "$(cat /tmp/homologacao.json)" "docker-compose.homologacao.yml"

echo "DATABASE_URL_MIGRACAO só no worker"
