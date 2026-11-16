#!/bin/sh
# Falha se a DATABASE_URL_MIGRACAO chegar a quem não deve (T-352, T-382, ADR 0040, item 9): é
# credencial com DDL em todos os schemas. Ela vai ao worker que lê a fila `banco` (a criação da
# empresa e o apagamento da cancelada, CELERY_TASK_ROUTES) e ao `migrar`, e a mais ninguém: nem ao
# backend (web), nem ao beat, nem a outro worker; e nenhum outro serviço lê essa fila.
#   desenvolvimento: um worker só, que lê `celery,banco` e recebe a credencial
#   homologação e produção: `worker` (só `celery`, sem a credencial), `worker-banco` (só `banco`,
#   sem beat, com a credencial) e o `migrar` (migrate_schemas, sai em seguida)
# A fila é conferida pelo argumento exato de `-Q`/`--queues` (separado por vírgula), não por
# `banco` em qualquer parte do comando.
set -e
cd "$(dirname "$0")/../.."

command -v jq >/dev/null || { echo "jq não encontrado"; exit 1; }

# Filas do serviço: o argumento seguinte a -Q/--queues (ou --queues=...), separado por vírgula.
FILAS='def filas: (.command // []) as $c
  | [range(0; $c | length) as $i
     | if ($c[$i] == "-Q" or $c[$i] == "--queues") then ($c[$i + 1] // "")
       elif ($c[$i] | startswith("--queues=")) then ($c[$i] | ltrimstr("--queues="))
       elif ($c[$i] | test("^-Q.+")) then ($c[$i] | ltrimstr("-Q"))
       else empty end]
  | map(split(",")) | add // [];
def com_beat: (.command // []) | any(. == "-B" or . == "--beat" or . == "beat");'

# conferir <json> <rótulo> <worker com a credencial> <filas exatas dele> <pode ter migrar: sim|nao>
conferir() {
  json=$1
  rotulo=$2
  com=$3
  filas_do_com=$4
  for servico in $(echo "$json" | jq -r '.services | keys[]'); do
    s() { echo "$json" | jq -r --arg s "$servico" "$FILAS .services[\$s] | $1"; }
    valor=$(echo "$json" | jq -r --arg s "$servico" '.services[$s].environment.DATABASE_URL_MIGRACAO // ""')
    filas=$(s 'filas | join(",")')
    le_banco=$(s 'filas | index("banco") != null')
    if [ "$servico" = "$com" ]; then
      [ -n "$valor" ] || { echo "$rotulo: $com não recebe a DATABASE_URL_MIGRACAO."; exit 1; }
      [ "$filas" = "$filas_do_com" ] || { echo "$rotulo: $com lê '$filas'; deve ler exatamente '$filas_do_com'."; exit 1; }
      [ "$(s com_beat)" = false ] || { echo "$rotulo: $com não pode rodar o beat."; exit 1; }
      if [ "$5" = sim ]; then
        # GIRO_WORKER=banco liga a lista fechada de tarefas (ADR 0040, item 10).
        giro_worker=$(echo "$json" | jq -r --arg s "$servico" '.services[$s].environment.GIRO_WORKER // ""')
        [ "$giro_worker" = banco ] || { echo "$rotulo: $com sem GIRO_WORKER=banco."; exit 1; }
      fi
    elif [ "$servico" = migrar ] && [ "$5" = sim ]; then
      # `migrar` recebe a credencial para o migrate_schemas e sai; não é worker.
      [ "$le_banco" = false ] || { echo "$rotulo: migrar lê a fila banco."; exit 1; }
    else
      [ -z "$valor" ] || { echo "$rotulo: $servico recebe a DATABASE_URL_MIGRACAO; só $com pode."; exit 1; }
      [ "$le_banco" = false ] || { echo "$rotulo: $servico lê a fila banco; só $com pode."; exit 1; }
    fi
  done
  echo "$json" | jq -e --arg c "$com" '.services[$c]' >/dev/null || { echo "$rotulo: falta o serviço $com."; exit 1; }
}

# Desenvolvimento: o valor vem do .env, que o worker lê por env_file.
cp .env.example .env
conferir "$(docker compose config --format json)" "docker-compose.yml" worker "celery,banco" nao

# Homologação: o modelo traz o valor vazio, então o check usa um valor de teste na interpolação.
DATABASE_URL_MIGRACAO=postgres://giro_migracao:so-para-o-check@db:5432/giro \
  ENV_FILE=homologacao.env.example DOMINIO_BASE=exemplo.test FRONTEND_UPSTREAM=frontend:3000 \
  ADMIN_IPS_ARQUIVO=./homologacao.admin-ips.conf.example CERT_DIR_HOST=. \
  docker compose -f infra/deploy/docker-compose.homologacao.yml config --format json > /tmp/homologacao.json
conferir "$(cat /tmp/homologacao.json)" "docker-compose.homologacao.yml" worker-banco "banco" sim

# Produção: os mesmos valores de teste que o check-producao.sh usa na interpolação.
rm -f /tmp/producao.json
GIRO_SO_CONFIG=/tmp/producao.json sh infra/scripts/check-producao.sh >/dev/null 2>&1 || true
if [ ! -s /tmp/producao.json ]; then
  echo "Não consegui montar o compose de produção para conferir."; exit 1
fi
conferir "$(cat /tmp/producao.json)" "docker-compose.producao.yml" worker-banco "banco" sim

echo "DATABASE_URL_MIGRACAO só no worker-banco (fila banco, exata) e no migrar, nos três compose"
