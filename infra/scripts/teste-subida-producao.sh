#!/bin/sh
# Teste de subida da imagem `producao` do backend (T-264, ADR 0027), no compose de homologação
# com banco e Redis descartáveis. Confere: processo 1 é o Gunicorn com 2 workers gthread e sem
# root; uma requisição pelo proxy chega ao Django; e `docker stop` deixa a requisição em curso
# terminar. Uso: sh infra/scripts/teste-subida-producao.sh   (precisa de Docker com Compose v2)
set -eu
cd "$(dirname "$0")/../.."

PROJETO=giro-subida-teste
TMP=$(mktemp -d)
# No Git Bash do Windows o Docker precisa do caminho no formato C:/...
TMPW=$(cygpath -m "$TMP" 2>/dev/null || echo "$TMP")
RAIZW=$(cygpath -m "$(pwd)" 2>/dev/null || pwd)
FALHAS=0
COMPOSE="docker compose -p $PROJETO -f infra/deploy/docker-compose.homologacao.yml -f $TMPW/banco.yml --env-file $TMPW/teste.env"

limpar() {
  $COMPOSE down -v --remove-orphans >/dev/null 2>&1 || true
  docker rm -f "$PROJETO-lento" >/dev/null 2>&1 || true
  rm -rf "$TMP"
}
trap limpar EXIT

confere() { # descrição, comando
  if sh -c "$2" >/dev/null 2>&1; then echo "ok    $1"; else echo "FALHA $1"; FALHAS=$((FALHAS + 1)); fi
}

mkdir -p "$TMP/cert"
cp infra/deploy/homologacao.admin-ips.conf.example "$TMP/admin-ips.conf"  # o modelo entregue: vazio
docker run --rm -v "$TMPW/cert:/c" nginx:1.27 sh -c \
  'openssl req -x509 -newkey rsa:2048 -nodes -keyout /c/privkey.pem -out /c/fullchain.pem -subj /CN=teste -days 1 2>/dev/null'

# Variáveis de homologação (infra/deploy/homologacao.env.example) com valores de teste.
# Papéis separados (ADR 0016, corrigido na T-276): a migração entra como giro_migracao e o
# serviço como giro_app. Banco e Redis só com senha (T-274).
CHAVE_A=$(python3 -c 'import base64,os;print("1:"+base64.b64encode(os.urandom(32)).decode())' 2>/dev/null   || python -c 'import base64,os;print("1:"+base64.b64encode(os.urandom(32)).decode())')
CHAVE_B=$(python3 -c 'import base64,os;print("1:"+base64.b64encode(os.urandom(32)).decode())' 2>/dev/null   || python -c 'import base64,os;print("1:"+base64.b64encode(os.urandom(32)).decode())')
cat > "$TMP/teste.env" <<ENV
DJANGO_SETTINGS_MODULE=config.settings.prod
DOMINIO_BASE=homolog.teste
DJANGO_ALLOWED_HOSTS=.homolog.teste
DJANGO_CSRF_TRUSTED_ORIGINS=https://admin.homolog.teste
DJANGO_SECRET_KEY=segredo-de-teste-do-django-so-para-esta-subida
JWT_SIGNING_KEY=segredo-de-teste-dos-tokens-so-para-esta-subida
DJANGO_HSTS_SEGUNDOS=86400
DJANGO_HSTS_PRELOAD=0
GIRO_EXPOR_DOCUMENTACAO_DA_API=0
GIRO_PROXIES_CONFIAVEIS=1
GIRO_REDES_PROXY=172.16.0.0/12
GIRO_CHAVE_DADOS_PESSOAIS=$CHAVE_A
GIRO_CHAVE_SEGREDOS=$CHAVE_B
GIRO_PEPPER_HMAC=pepper-de-teste-com-mais-de-trinta-e-dois-bytes-aleatorios
DATABASE_URL=postgres://giro_app:senha-app@db:5432/giro
DATABASE_URL_MIGRACAO=postgres://giro_migracao:senha-migracao@db:5432/giro
REDIS_URL=redis://:senha-do-redis@redis:6379/0
CELERY_BROKER_URL=redis://:senha-do-redis@redis:6379/1
CELERY_RESULT_BACKEND=redis://:senha-do-redis@redis:6379/2
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.teste.invalido
GIRO_ARMAZENAMENTO=s3
S3_BUCKET=teste
S3_REGIAO=sa-east-1
S3_CHAVE_DE_ACESSO=teste
S3_CHAVE_SECRETA=teste
GIRO_PROVEDOR_PAGAMENTOS=asaas
GIRO_ASAAS_URL=https://api-sandbox.asaas.com/v3
GIRO_ASAAS_CHAVE_API=chave-de-teste
SENTRY_ENVIRONMENT=teste
GUNICORN_WORKERS=2
GUNICORN_THREADS=4
GUNICORN_TIMEOUT=30
CERT_DIR_HOST=$TMPW/cert
FRONTEND_UPSTREAM=frontend:3000
ADMIN_IPS_ARQUIVO=$TMPW/admin-ips.conf
PORTA_HTTP=18080
PORTA_HTTPS=18443
ENV_FILE=$TMPW/teste.env
ENV

cat > "$TMP/banco.yml" <<YML
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: giro
      POSTGRES_USER: giro
      POSTGRES_PASSWORD: senha-admin
      POSTGRES_PASSWORD_MIGRACAO: senha-migracao
      POSTGRES_PASSWORD_APP: senha-app
    volumes:
      - $RAIZW/infra/postgres:/docker-entrypoint-initdb.d:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U giro -d giro"]
      interval: 3s
      timeout: 3s
      retries: 20
  frontend:
    # Next de mentira: qualquer GET responde "NEXT", para ver o que o proxy manda para o frontend.
    image: python:3.12-slim-bookworm
    command:
      - python
      - -c
      - |
        import http.server
        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(s):
                s.send_response(200); s.end_headers(); s.wfile.write(b"NEXT")
            def log_message(*a): pass
        http.server.ThreadingHTTPServer(("0.0.0.0", 3000), H).serve_forever()
  proxy:
    depends_on:
      frontend: {condition: service_started}
  redis:
    image: redis:7-alpine
    command: ["redis-server", "--requirepass", "senha-do-redis"]
  migrar:
    depends_on:
      db: {condition: service_healthy}
  backend:
    depends_on:
      db: {condition: service_healthy}
      redis: {condition: service_started}
YML

echo "Subindo (build, migração e proxy)..."
$COMPOSE up -d --build || { $COMPOSE logs --tail=30 migrar backend; echo "FALHA a subida"; exit 1; }

echo "Esperando o backend responder..."
n=0
# O código HTTP, não o status do curl: o curl do Windows (schannel) sai com erro mesmo com 200.
until [ "$(curl -sk -o /dev/null -w '%{http_code}' -H "Host: admin.homolog.teste" https://127.0.0.1:18443/api/plataforma/ambiente/ 2>/dev/null)" = 200 ]; do
  n=$((n + 1)); [ $n -gt 60 ] && { $COMPOSE ps -a; $COMPOSE logs --tail=40 proxy backend; echo "FALHA backend não subiu"; exit 1; }
  sleep 2
done

B=$($COMPOSE ps -q backend)
confere "processo 1 do backend é o Gunicorn" \
  "docker exec $B sh -c 'tr \"\0\" \" \" < /proc/1/cmdline' | grep -q '^gunicorn\|/gunicorn'"
confere "mestre com 2 workers"   "[ \$(docker exec $B cat /proc/1/task/1/children | wc -w) -eq 2 ]"
confere "classe de worker gthread com 4 threads" \
  "docker exec $B gunicorn -c /app/gunicorn.conf.py --print-config config.wsgi:application | grep -q 'worker_class *= gthread' && docker exec $B gunicorn -c /app/gunicorn.conf.py --print-config config.wsgi:application | grep -q 'threads *= 4'"
confere "backend roda sem root" "[ \$(docker exec $B id -u) -ne 0 ]"
confere "backend sem pytest (só requirements.txt)" "! docker exec $B python -c 'import pytest'"
CODIGO=$(curl -sk -o /dev/null -w '%{http_code}' -H "Host: admin.homolog.teste" https://127.0.0.1:18443/api/plataforma/ambiente/ || true)
confere "requisição pelo proxy chegou ao Django (HTTP $CODIGO)" "[ $CODIGO -ge 200 ] && [ $CODIGO -lt 500 ]"
confere "estático do Admin servido pelo proxy" \
  "[ \"\$(curl -sk -o /dev/null -w '%{http_code}' -H 'Host: admin.homolog.teste' https://127.0.0.1:18443/static/admin/css/base.css)\" = 200 ]"
confere "worker e beat de pé" "[ \$($COMPOSE ps -q worker beat | wc -l) -eq 2 ]"

# Banco e Redis só com senha (T-274): o serviço recusa sem ela e os dois a exigem de quem chega.
REDE="${PROJETO}_default"
confere "Redis recusa quem não manda a senha"   "docker run --rm --network $REDE redis:7-alpine redis-cli -h redis ping | grep -q NOAUTH"
confere "Redis atende com a senha"   "docker run --rm --network $REDE redis:7-alpine redis-cli -h redis -a senha-do-redis --no-auth-warning ping | grep -q PONG"
confere "Postgres recusa o papel do serviço sem senha"   "! docker run --rm --network $REDE postgres:16 psql 'postgres://giro_app@db:5432/giro' -w -c 'select 1'"
confere "Postgres atende com a senha"   "docker run --rm --network $REDE postgres:16 psql 'postgres://giro_app:senha-app@db:5432/giro' -w -c 'select 1'"
recusa_sem_senha() { # variável, valor sem senha, trecho esperado da mensagem
  SAIDA=$(docker run --rm --env-file "$TMPW/teste.env" -e "$1=$2" --entrypoint python     giro-backend:producao -c 'from django.conf import settings; settings.DEBUG' 2>&1 || true)
  if echo "$SAIDA" | grep -q "$3"; then
    echo "ok    imagem producao recusa $1 sem senha"
  else
    echo "FALHA imagem producao recusa $1 sem senha"; FALHAS=$((FALHAS + 1))
  fi
}
recusa_sem_senha DATABASE_URL "postgres://giro_app@db:5432/giro" "DATABASE_URL sem senha"
recusa_sem_senha REDIS_URL "redis://redis:6379/0" "REDIS_URL sem senha"
recusa_sem_senha CELERY_BROKER_URL "redis://redis:6379/1" "CELERY_BROKER_URL sem senha"

# Django Admin pelo proxy (T-291, ADR 0029): fechado com a lista de IPs vazia (o modelo do cofre),
# aberto só para o IP que entra na lista, e o Next intacto nos hosts das empresas.
PLAT="admin.homolog.teste"
EMP="motorapida.homolog.teste"
IPCLIENTE=$($COMPOSE logs proxy 2>/dev/null | grep -m1 'GET /api/plataforma/ambiente/' \
  | sed -E 's/.*\| +([0-9a-fA-F:.]+) - -.*/\1/')
http() { # host, caminho: devolve o código; corpo em $TMP/corpo e cabeçalhos em $TMP/cab
  curl -sk -o "$TMPW/corpo" -D "$TMPW/cab" -w '%{http_code}' -H "Host: $1" "https://127.0.0.1:18443$2" || true
}
verifica() { # descrição, obtido, esperado
  if [ "$2" = "$3" ]; then echo "ok    $1"; else echo "FALHA $1 (esperava $3, veio $2)"; FALHAS=$((FALHAS + 1)); fi
}
[ -n "$IPCLIENTE" ] || { echo "FALHA não achei o IP do cliente no log do proxy"; FALHAS=$((FALHAS + 1)); }
verifica "Admin fechado com a lista vazia: /admin/ dá 404" "$(http $PLAT /admin/)" 404
verifica "Admin fechado com a lista vazia: /admin/login/ dá 404" "$(http $PLAT /admin/login/)" 404
verifica "host da plataforma segue no Next em /" "$(http $PLAT /; cat "$TMP/corpo")" "200NEXT"
verifica "host da empresa: /admin/contratos fica no Next" "$(http $EMP /admin/contratos; cat "$TMP/corpo")" "200NEXT"
echo "$IPCLIENTE 1;" > "$TMP/admin-ips.conf"
$COMPOSE exec -T proxy nginx -s reload >/dev/null 2>&1
sleep 2
verifica "IP na lista: /admin/login/ responde 200" "$(http $PLAT /admin/login/)" 200
confere "IP na lista: é a tela de login do Django" "grep -q csrfmiddlewaretoken $TMP/corpo"
confere "IP na lista: resposta com X-Robots-Tag noindex" "grep -qi '^x-robots-tag: noindex' $TMP/cab"
verifica "IP na lista: login com os estáticos (login.css)" "$(http $PLAT /static/admin/css/login.css)" 200
verifica "host da empresa continua no Next com o IP na lista" "$(http $EMP /admin/login/; cat "$TMP/corpo")" "200NEXT"
: > "$TMP/admin-ips.conf"
$COMPOSE exec -T proxy nginx -s reload >/dev/null 2>&1
sleep 2
verifica "lista esvaziada de novo: /admin/login/ volta a dar 404" "$(http $PLAT /admin/login/)" 404

# docker stop com requisição em curso: aplicação de 8 s atrás do mesmo gunicorn.conf.py.
mkdir -p "$TMP/lento"
printf 'import time\ndef app(env, resp):\n    time.sleep(8)\n    resp("200 OK", [("Content-Type", "text/plain")])\n    return [b"terminou"]\n' > "$TMP/lento/lento.py"
docker run -d --name "$PROJETO-lento" -v "$TMPW/lento:/lento:ro" -w /lento --entrypoint gunicorn \
  -p 18090:8000 giro-backend:producao -c /app/gunicorn.conf.py lento:app >/dev/null
sleep 3
( curl -s -m 30 -o "$TMPW/resposta" -w '%{http_code}' http://127.0.0.1:18090/ > "$TMP/codigo" ) &
sleep 2
docker stop -t 40 "$PROJETO-lento" >/dev/null
wait
confere "docker stop deixou a requisição de 8 s terminar (HTTP $(cat "$TMP/codigo"))" \
  "[ \"\$(cat $TMP/codigo)\" = 200 ] && grep -q terminou $TMP/resposta"
confere "contêiner saiu com 0" "[ \$(docker inspect -f '{{.State.ExitCode}}' $PROJETO-lento) -eq 0 ]"

[ "$FALHAS" -eq 0 ] && echo "Subida da imagem producao: tudo certo." || { echo "$FALHAS falha(s)."; exit 1; }
