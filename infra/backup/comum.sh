#!/bin/sh
# Variáveis comuns dos scripts de backup, certificado e monitoramento da produção (T-373).
# Para usar com `. "$(dirname "$0")/comum.sh"`. Roda na VPS, como o usuário que opera o compose.
#   GIRO_SEGREDOS  pasta dos arquivos gerados do cofre (padrão /etc/giro, dono do operador, 700):
#                  producao.env, producao-infra.env, admin-ips.conf e cloudflare.ini (600)
RAIZ=$(cd "$(dirname "$0")/../.." && pwd)
SEGREDOS=${GIRO_SEGREDOS:-/etc/giro}

export ENV_FILE="$SEGREDOS/producao.env"
export ADMIN_IPS_ARQUIVO="$SEGREDOS/admin-ips.conf"
export CLOUDFLARE_INI_ARQUIVO="$SEGREDOS/cloudflare.ini"

COMPOSE="docker compose -f $RAIZ/infra/deploy/docker-compose.producao.yml --env-file $SEGREDOS/producao.env --env-file $SEGREDOS/producao-infra.env"

# valor_infra NOME: lê uma variável de producao-infra.env sem carregar o arquivo no shell.
valor_infra() {
  grep "^$1=" "$SEGREDOS/producao-infra.env" | head -n 1 | cut -d= -f2-
}

registrar() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') $*"
}
