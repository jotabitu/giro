#!/bin/sh
# Constrói as imagens de produção na máquina da equipe e as leva à VPS sem build nela (T-473).
# Perfil 4 GB (T-471): o `next build` e a imagem do backend não cabem na VPS ao lado do sistema.
# Roda no Git Bash do Windows e no Linux. Não usa segredo: nenhuma das imagens leva segredo.
#
# Uso: sh infra/deploy/enviar-imagens.sh [versao]
#   versao            tag extra das imagens (padrão: git describe --tags --always)
# Variáveis:
#   GIRO_VPS          destino do ssh (padrão giro@187.53.112.199)
#   GIRO_PLATAFORMA   plataforma do build (padrão linux/amd64, a da VPS)
#   API_URL_INTERNA   build arg do frontend (padrão do Dockerfile: http://backend:8000); não é segredo
#   SO_CONSTRUIR=1    constrói e marca, mas não envia
#
# Cada imagem recebe duas tags: `producao` (a que o compose usa por padrão) e a versão. Para
# subir uma versão específica na VPS (rollback): GIRO_TAG=<versao> docker compose ... up -d.
set -eu
cd "$(dirname "$0")/../.."

VERSAO=${1:-$(git describe --tags --always)}
VPS=${GIRO_VPS:-giro@187.53.112.199}
PLATAFORMA=${GIRO_PLATAFORMA:-linux/amd64}

if ! docker info >/dev/null 2>&1; then
  echo "Docker local fora do ar. Ligue o Docker Desktop e tente de novo." >&2
  exit 1
fi

construir() { # nome dockerfile [argumentos extras do docker build]
  nome=$1
  arquivo=$2
  shift 2
  echo "==> $nome:$VERSAO ($PLATAFORMA)"
  docker build --platform "$PLATAFORMA" -f "$arquivo" -t "$nome:producao" -t "$nome:$VERSAO" "$@" .
}

# Um build por vez: a máquina da equipe também tem pouca memória.
construir giro-postgres infra/docker/postgres.Dockerfile
construir giro-backend infra/docker/backend.Dockerfile --target producao
if [ -n "${API_URL_INTERNA:-}" ]; then
  construir giro-frontend infra/docker/frontend.producao.Dockerfile --build-arg "API_URL_INTERNA=$API_URL_INTERNA"
else
  construir giro-frontend infra/docker/frontend.producao.Dockerfile
fi

IMAGENS=""
for n in giro-postgres giro-backend giro-frontend; do
  IMAGENS="$IMAGENS $n:producao $n:$VERSAO"
done
echo "==> Tamanho (descomprimido; o envio com gzip fica em cerca de um terço)"
for i in $IMAGENS; do
  docker image inspect --format "$i  {{.Size}} bytes" "$i"
done

if [ "${SO_CONSTRUIR:-}" = "1" ]; then
  echo "SO_CONSTRUIR=1: imagens marcadas como producao e $VERSAO; nada enviado."
  exit 0
fi

echo "==> Enviando para $VPS (docker save | gzip | ssh docker load)"
# shellcheck disable=SC2086
docker save $IMAGENS | gzip | ssh "$VPS" 'gunzip | docker load'
echo "Pronto. Na VPS: git checkout $VERSAO, baixar-segredos.sh e up -d sem --build (infra/README.md)."
