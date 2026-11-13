#!/bin/sh
# Gera os arquivos de segredos da produção a partir do cofre (T-373, ADR 0033, item 5). Os arquivos
# ficam em GIRO_SEGREDOS (padrão /etc/giro) com permissão 600 e a pasta com 700; nada vai para o
# repositório. Dois conjuntos, porque a aplicação não pode ter a credencial de backup nem a do DNS:
#   producao.env        a aplicação (modelo: producao.env.example)
#   producao-infra.env  banco, Redis, backup, certificado, alerta (modelo: producao-infra.env.example)
# Mais dois arquivos, sem formato de variável: admin-ips.conf (IPs do Django Admin, ADR 0029; vazio
# por padrão) e cloudflare.ini (`dns_cloudflare_api_token = <token>`).
#
# Uso: COFRE=doppler sh infra/deploy/baixar-segredos.sh
#        precisa do CLI `doppler` autenticado com um token de serviço só de leitura;
#        configs `prd` (aplicação) e `prd_infra` (infra) do projeto `giro`. Com DOPPLER_TOKEN_APP e
#        DOPPLER_TOKEN_INFRA (no ambiente ou em $GIRO_SEGREDOS/doppler.env), um token por config.
#      COFRE=bws sh infra/deploy/baixar-segredos.sh
#        precisa do CLI `bws` e de BWS_ACCESS_TOKEN (conta de máquina só de leitura) e jq;
#        BWS_PROJETO_APP e BWS_PROJETO_INFRA com os IDs dos projetos do Secrets Manager.
# Os segredos `ADMIN_IPS` e `CLOUDFLARE_API_TOKEN` viram os arquivos acima.
set -eu

SEGREDOS=${GIRO_SEGREDOS:-/etc/giro}
umask 077
mkdir -p "$SEGREDOS"
chmod 700 "$SEGREDOS"

case "${COFRE:-}" in
  doppler)
    # Tokens de serviço por config (T-473): DOPPLER_TOKEN_APP (prd) e DOPPLER_TOKEN_INFRA
    # (prd_infra), do ambiente ou de $SEGREDOS/doppler.env (600). Cada um vai só ao seu comando,
    # pela variável (não pela linha de comando, que aparece no `ps`). Sem eles, vale o login do CLI.
    if [ -f "$SEGREDOS/doppler.env" ]; then
      # shellcheck disable=SC1091
      . "$SEGREDOS/doppler.env"
    fi
    if [ -n "${DOPPLER_TOKEN_APP:-}" ] && [ -n "${DOPPLER_TOKEN_INFRA:-}" ]; then
      DOPPLER_TOKEN="$DOPPLER_TOKEN_APP" doppler secrets download --project giro --config prd --format env --no-file > "$SEGREDOS/producao.env"
      DOPPLER_TOKEN="$DOPPLER_TOKEN_INFRA" doppler secrets download --project giro --config prd_infra --format env --no-file > "$SEGREDOS/producao-infra.env"
    elif [ -n "${DOPPLER_TOKEN_APP:-}${DOPPLER_TOKEN_INFRA:-}" ]; then
      echo "defina DOPPLER_TOKEN_APP e DOPPLER_TOKEN_INFRA juntos (ou nenhum, para usar o login do CLI)" >&2
      exit 1
    else
      doppler secrets download --project giro --config prd --format env --no-file > "$SEGREDOS/producao.env"
      doppler secrets download --project giro --config prd_infra --format env --no-file > "$SEGREDOS/producao-infra.env"
    fi
    ;;
  bws)
    : "${BWS_PROJETO_APP:?defina BWS_PROJETO_APP}" "${BWS_PROJETO_INFRA:?defina BWS_PROJETO_INFRA}"
    bws secret list "$BWS_PROJETO_APP" --output json | jq -r '.[] | "\(.key)=\(.value)"' > "$SEGREDOS/producao.env"
    bws secret list "$BWS_PROJETO_INFRA" --output json | jq -r '.[] | "\(.key)=\(.value)"' > "$SEGREDOS/producao-infra.env"
    ;;
  *)
    echo "defina COFRE=doppler ou COFRE=bws (ver o cabeçalho deste script)"
    exit 2
    ;;
esac

# Arquivos que não são variáveis. ADMIN_IPS vem do cofre em linhas `<ip> 1;` separadas por
# "\n" literal (vazio = Admin fechado).
valor() { grep "^$1=" "$SEGREDOS/producao-infra.env" | head -n 1 | cut -d= -f2-; }
printf '%s\n' "$(valor ADMIN_IPS | sed 's/\\n/\n/g')" > "$SEGREDOS/admin-ips.conf"
printf 'dns_cloudflare_api_token = %s\n' "$(valor CLOUDFLARE_API_TOKEN)" > "$SEGREDOS/cloudflare.ini"
sed -i '/^ADMIN_IPS=/d' "$SEGREDOS/producao-infra.env"
chmod 600 "$SEGREDOS"/*
echo "segredos gravados em $SEGREDOS (permissão 600)"
