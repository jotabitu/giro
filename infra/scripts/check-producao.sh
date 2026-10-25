#!/bin/sh
# Confere o compose de produção (T-373, ADR 0033) com valores de teste: o `docker compose config`
# passa e infra/scripts/check-producao.mjs confere as regras de rede e de segredo. Roda no job
# Infra do CI e na máquina de quem mexe no compose. Uso: sh infra/scripts/check-producao.sh
set -e
cd "$(dirname "$0")/../.."

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
TMPW=$(cygpath -m "$TMP" 2>/dev/null || echo "$TMP")

# Aplicação: o modelo entregue mais os valores de teste das variáveis que o compose exige.
cat > "$TMP/producao.env" <<ENV
DOMINIO_BASE=exemplo.test
DATABASE_URL_MIGRACAO=postgres://giro_migracao:so-para-o-check@db:5432/giro
ENV
# Infra: valores de teste, um para cada variável obrigatória do modelo.
cat > "$TMP/producao-infra.env" <<ENV
POSTGRES_DB=giro
POSTGRES_USER=giro
POSTGRES_PASSWORD=so-para-o-check
POSTGRES_PASSWORD_MIGRACAO=so-para-o-check
POSTGRES_PASSWORD_APP=so-para-o-check
REDIS_SENHA=so-para-o-check
PGBACKREST_REPO1_S3_BUCKET=bucket-de-teste
PGBACKREST_REPO1_S3_ENDPOINT=s3.exemplo.test
PGBACKREST_REPO1_S3_REGION=regiao
PGBACKREST_REPO1_S3_KEY=chave-de-teste
PGBACKREST_REPO1_S3_KEY_SECRET=segredo-de-teste
PGBACKREST_REPO1_CIPHER_PASS=cifra-de-teste
ARQUIVOS_S3_ENDPOINT=https://s3.exemplo.test
ARQUIVOS_S3_BUCKET=arquivos-de-teste
ARQUIVOS_S3_CHAVE_LEITURA=chave-de-teste
ARQUIVOS_S3_SEGREDO_LEITURA=segredo-de-teste
RESTIC_REPOSITORY=s3:https://s3.exemplo.test/bucket-de-teste/arquivos
RESTIC_PASSWORD=restic-de-teste
AWS_ACCESS_KEY_ID=chave-de-teste
AWS_SECRET_ACCESS_KEY=segredo-de-teste
CERTBOT_EMAIL=teste@exemplo.test
ENV
cp infra/deploy/producao.admin-ips.conf.example "$TMP/admin-ips.conf"
echo "dns_cloudflare_api_token = so-para-o-check" > "$TMP/cloudflare.ini"

ENV_FILE="$TMPW/producao.env" ADMIN_IPS_ARQUIVO="$TMPW/admin-ips.conf" CLOUDFLARE_INI_ARQUIVO="$TMPW/cloudflare.ini" \
  docker compose -f infra/deploy/docker-compose.producao.yml --profile certificado --profile backup \
  --env-file "$TMP/producao.env" --env-file "$TMP/producao-infra.env" config --format json > "$TMP/config.json"

node infra/scripts/check-producao.mjs "$TMP/config.json"
