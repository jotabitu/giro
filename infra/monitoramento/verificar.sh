#!/bin/sh
# Monitoramento da VPS de produção (T-373, ADR 0033): saúde do Postgres, disco, memória,
# serviços do compose, falha do backup e validade do certificado. Sem agente nem painel: um
# timer do systemd roda este script e ele avisa por e-mail (SMTP com TLS) quando algo sai do
# normal, uma vez a cada 6 horas por problema, e avisa de novo quando o problema some.
#
# Uso: sh infra/monitoramento/verificar.sh rapido    (a cada 5 min: serviços, Postgres, disco, memória, certificado)
#      sh infra/monitoramento/verificar.sh completo  (de hora em hora: tudo isso e a idade dos backups)
# Precisa de curl e openssl no host. Variáveis ALERTA_* e BATIMENTO_URL: producao-infra.env.
set -u
. "$(dirname "$0")/../backup/comum.sh"

MODO=${1:-rapido}
ESTADO=${GIRO_ESTADO_MONITORAMENTO:-/var/lib/giro-monitoramento}
mkdir -p "$ESTADO"
PROBLEMAS=""
REAVISO=21600   # 6 horas

DISCO_AVISO=80
DISCO_CRITICO=90
CERT_DIAS=21
BACKUP_HORAS=26
CONEXOES_PCT=80
IDADE_XID=1500000000

problema() { # chave, mensagem
  PROBLEMAS="$PROBLEMAS $1"
  agora=$(date +%s)
  arquivo="$ESTADO/$1"
  ultimo=0
  [ -f "$arquivo" ] && ultimo=$(cat "$arquivo")
  if [ $((agora - ultimo)) -ge $REAVISO ]; then
    avisar "Giro produção: $1" "$2"
    echo "$agora" > "$arquivo"
  fi
  registrar "PROBLEMA $1: $2"
}

avisar() { # assunto, corpo
  [ -n "$(valor_infra ALERTA_SMTP_URL)" ] || { registrar "ALERTA_SMTP_URL vazia: aviso não enviado"; return 0; }
  de=$(valor_infra ALERTA_DE)
  para=$(valor_infra ALERTA_PARA)
  corpo=$(printf 'From: %s\nTo: %s\nSubject: %s\nContent-Type: text/plain; charset=UTF-8\n\n%s\n\nHost: %s\nQuando: %s\n' \
    "$de" "$para" "$1" "$2" "$(hostname)" "$(date)")
  set --
  for dest in $(echo "$para" | tr ',' ' '); do set -- "$@" --mail-rcpt "$dest"; done
  echo "$corpo" | curl -sS --ssl-reqd --url "$(valor_infra ALERTA_SMTP_URL)" --mail-from "$de" "$@" \
    --user "$(valor_infra ALERTA_USUARIO):$(valor_infra ALERTA_SENHA)" -T - >/dev/null \
    || registrar "falha ao enviar o aviso por e-mail"
}

# Problemas que sumiram: apaga o estado e avisa que voltou ao normal.
resolver_os_que_sumiram() {
  for arquivo in "$ESTADO"/*; do
    [ -f "$arquivo" ] || continue
    chave=$(basename "$arquivo")
    case " $PROBLEMAS " in *" $chave "*) ;; *)
      # No modo rápido, só encerra o que o modo rápido verifica.
      if [ "$MODO" = completo ] || ! echo "$chave" | grep -q '^backup'; then
        rm -f "$arquivo"; avisar "Giro produção: $chave resolvido" "O problema $chave não aparece mais."
      fi ;;
    esac
  done
}

# 1. Serviços do compose de pé.
esperados="db redis backend worker worker-apagamento beat frontend proxy"
rodando=$($COMPOSE ps --status running --services 2>/dev/null)
for s in $esperados; do
  echo "$rodando" | grep -qx "$s" || problema "servico-$s-parado" "O serviço $s não está rodando."
done

# 2. Postgres.
if $COMPOSE exec -T db pg_isready -U "$(valor_infra POSTGRES_USER)" -d "$(valor_infra POSTGRES_DB)" >/dev/null 2>&1; then
  sql() { $COMPOSE exec -T db psql -U "$(valor_infra POSTGRES_USER)" -d "$(valor_infra POSTGRES_DB)" -tAc "$1" 2>/dev/null; }
  usadas=$(sql "SELECT count(*) FROM pg_stat_activity")
  maximo=$(sql "SHOW max_connections")
  if [ -n "$usadas" ] && [ -n "$maximo" ] && [ $((usadas * 100 / maximo)) -ge $CONEXOES_PCT ]; then
    problema "postgres-conexoes" "Conexões em uso: $usadas de $maximo."
  fi
  # Arquivamento de WAL (base do backup contínuo): a última tentativa não pode ter falhado depois do último sucesso.
  falhou=$(sql "SELECT COALESCE(last_failed_time > COALESCE(last_archived_time, 'epoch'), false) FROM pg_stat_archiver")
  [ "$falhou" = t ] && problema "postgres-wal-arquivamento" "O arquivamento de WAL para o pgBackRest está falhando; o WAL se acumula no disco."
  idade=$(sql "SELECT max(age(datfrozenxid)) FROM pg_database")
  [ -n "$idade" ] && [ "$idade" -ge $IDADE_XID ] && problema "postgres-vacuum" "Idade de transação em $idade: o autovacuum não está dando conta."
  tamanho=$(sql "SELECT pg_size_pretty(pg_database_size(current_database()))")
  registrar "postgres ok: $usadas/$maximo conexões, banco com $tamanho"
else
  problema "postgres-fora" "O Postgres não responde ao pg_isready."
fi

# 3. Disco da VPS e do volume do Docker; memória.
for ponto in / /var/lib/docker; do
  [ -d "$ponto" ] || continue
  uso=$(df -P "$ponto" | awk 'NR==2 {gsub("%",""); print $5}')
  chave="disco-$(echo "$ponto" | tr '/' '_')"
  if [ "$uso" -ge $DISCO_CRITICO ]; then problema "$chave" "Disco $ponto com $uso% de uso (crítico, a partir de $DISCO_CRITICO%)."
  elif [ "$uso" -ge $DISCO_AVISO ]; then problema "$chave" "Disco $ponto com $uso% de uso (aviso, a partir de $DISCO_AVISO%)."
  fi
done
disp=$(awk '/MemAvailable/ {d=$2} /MemTotal/ {t=$2} END {print int(d*100/t)}' /proc/meminfo)
[ "$disp" -lt 10 ] && problema "memoria-baixa" "Só $disp% da memória disponível."

# 4. Certificado servido pelo proxy.
dominio=$(grep '^DOMINIO_BASE=' "$ENV_FILE" | cut -d= -f2-)
fim=$(echo | openssl s_client -connect 127.0.0.1:443 -servername "admin.$dominio" 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
if [ -n "$fim" ]; then
  dias=$(( ($(date -d "$fim" +%s) - $(date +%s)) / 86400 ))
  [ "$dias" -lt $CERT_DIAS ] && problema "certificado-vencendo" "O certificado vence em $dias dias ($fim). A renovação semanal não está funcionando."
else
  problema "certificado-ilegivel" "Não consegui ler o certificado servido em 127.0.0.1:443."
fi

# 5. Idade dos backups (modo completo).
if [ "$MODO" = completo ]; then
  limite=$((BACKUP_HORAS * 3600))
  ultimo=$($COMPOSE exec -T -u postgres db pgbackrest --stanza=giro --output=json info 2>/dev/null \
    | tr ',' '\n' | grep '"stop":' | tail -n 1 | grep -o '[0-9]\{9,\}')
  if [ -z "$ultimo" ]; then problema "backup-banco-sem-registro" "O pgBackRest não devolveu nenhum backup."
  elif [ $(( $(date +%s) - ultimo )) -gt $limite ]; then
    problema "backup-banco-atrasado" "O último backup do banco tem mais de $BACKUP_HORAS horas ($(date -d "@$ultimo"))."
  fi
  snap=$($COMPOSE --profile backup run --rm -T restic snapshots --latest 1 --tag arquivos --json 2>/dev/null \
    | grep -o '"time":"[^"]*"' | head -n 1 | cut -d'"' -f4)
  if [ -z "$snap" ]; then problema "backup-arquivos-sem-registro" "O restic não devolveu nenhum snapshot dos arquivos."
  elif [ $(( $(date +%s) - $(date -d "$snap" +%s) )) -gt $limite ]; then
    problema "backup-arquivos-atrasado" "O último snapshot dos arquivos tem mais de $BACKUP_HORAS horas ($snap)."
  fi
fi

resolver_os_que_sumiram

# Batimento: um serviço externo avisa se este script parar de rodar (VPS fora do ar).
ping=$(valor_infra BATIMENTO_URL)
if [ -n "$ping" ]; then
  if [ -z "$PROBLEMAS" ]; then curl -fsS -m 10 "$ping" >/dev/null 2>&1; else curl -fsS -m 10 "$ping/fail" >/dev/null 2>&1; fi
fi

[ -z "$PROBLEMAS" ] && registrar "verificação $MODO sem problemas"
exit 0
