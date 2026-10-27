#!/bin/sh
# Certificado curinga da produção (T-373, ADR 0033): Let's Encrypt por DNS-01 na Cloudflare, para
# DOMINIO_BASE e *.DOMINIO_BASE. O token da Cloudflare só tem permissão de DNS e vem do cofre
# (arquivo cloudflare.ini, 600, em GIRO_SEGREDOS).
# Uso: sh infra/deploy/certificado.sh emitir    (uma vez, antes de subir o proxy)
#      sh infra/deploy/certificado.sh renovar   (timer semanal; recarrega o nginx se renovou)
set -eu
. "$(dirname "$0")/../backup/comum.sh"

case "${1:-}" in
  emitir)
    $COMPOSE --profile certificado run --rm certificado
    ;;
  renovar)
    antes=$($COMPOSE --profile certificado run --rm --entrypoint sh certificado-renovar -c 'cat /etc/letsencrypt/live/*/fullchain.pem | sha256sum')
    $COMPOSE --profile certificado run --rm certificado-renovar
    depois=$($COMPOSE --profile certificado run --rm --entrypoint sh certificado-renovar -c 'cat /etc/letsencrypt/live/*/fullchain.pem | sha256sum')
    if [ "$antes" != "$depois" ]; then
      $COMPOSE exec -T proxy nginx -s reload
      registrar "certificado renovado e nginx recarregado"
    else
      registrar "certificado ainda válido, nada a renovar"
    fi
    ;;
  *)
    echo "uso: certificado.sh emitir|renovar"
    exit 2
    ;;
esac
