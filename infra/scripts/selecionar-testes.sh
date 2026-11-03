#!/bin/sh
# T-427: decide o que o CI roda. Lê da entrada padrão a lista de arquivos alterados (um por linha)
# e escreve "chave=valor" na saída padrão (o workflow acrescenta isso ao GITHUB_OUTPUT).
#
#   EVENTO  pull_request | push | outro (padrão: pull_request)
#   BASE    branch de destino do PR (padrão: develop)
#
# Seleção por arquivo só vale para PR com destino na develop. Push na develop, PR para a main e
# qualquer outro evento rodam a suíte inteira. Sem dependência nova: só sh, git e grep.
#
# Saídas: backend, frontend, infra (true/false: o job roda), backend_testes (tudo|lista|nenhum),
# backend_alvos (argumentos do pytest quando "lista"), frontend_testes (tudo|alterados).
set -eu

EVENTO=${EVENTO:-pull_request}
BASE=${BASE:-develop}
raiz=$(git rev-parse --show-toplevel)
cd "$raiz"

if [ "$EVENTO" != "pull_request" ] || [ "$BASE" != "develop" ]; then
  cat <<EOF
backend=true
frontend=true
infra=true
backend_testes=tudo
backend_alvos=
frontend_testes=tudo
EOF
  exit 0
fi

backend=false
frontend=false
infra=false
b_tudo=false
f_tudo=false
apps=""
arquivos=""

while IFS= read -r f; do
  [ -n "$f" ] || continue
  case "$f" in
    .github/workflows/*)
      backend=true; frontend=true; infra=true; b_tudo=true; f_tudo=true ;;
    docs/api/openapi.yaml)
      backend=true; frontend=true; b_tudo=true; f_tudo=true ;;
    infra/*|docker-compose*.yml|.env.example|Makefile)
      infra=true ;;
    backend/*.md)
      backend=true ;; # só texto: lint e OpenAPI rodam, pytest não
    backend/apps/*/migrations/*)
      backend=true; b_tudo=true ;; # o banco de teste nasce das migrações, e outros apps dependem delas
    backend/*/test_*.py)
      backend=true
      # arquivo de teste apagado não vai ao pytest
      if [ -f "$f" ]; then arquivos="$arquivos ${f#backend/}"; fi ;;
    backend/apps/*/*)
      backend=true
      app=${f#backend/apps/}; app=${app%%/*}
      case " $apps " in *" $app "*) ;; *) apps="$apps $app" ;; esac ;;
    backend/*)
      # config, comum, integracoes, seed, conftest, apoio dos testes, requirements, pyproject...
      backend=true; b_tudo=true ;;
    frontend/package.json|frontend/package-lock.json|frontend/vitest.config.*|frontend/tsconfig.json|frontend/src/lib/api/schema.d.ts|frontend/src/testes/*)
      frontend=true; f_tudo=true ;;
    frontend/*)
      frontend=true ;;
  esac
done

# Apps que importam um app alterado (direta ou indiretamente) entram também.
if [ "$b_tudo" = "false" ] && [ -n "$apps" ]; then
  mudou=true
  while [ "$mudou" = "true" ]; do
    mudou=false
    padrao=$(echo $apps | tr ' ' '|')
    for d in backend/apps/*/; do
      a=$(basename "$d")
      case " $apps " in *" $a "*) continue ;; esac
      if grep -rqE "(from|import) apps\.($padrao)\b" "$d" --include='*.py' --exclude-dir=tests --exclude-dir=migrations 2>/dev/null; then
        apps="$apps $a"
        mudou=true
      fi
    done
  done
fi

alvos=""
if [ "$b_tudo" = "false" ]; then
  for a in $apps; do
    [ -d "backend/apps/$a/tests" ] && alvos="$alvos apps/$a/tests"
  done
  if [ -n "$apps" ]; then
    padrao=$(echo $apps | tr ' ' '|')
    # Testes de aceitação, de comum e de integrações que citam o app (import, URL ou nome).
    for t in $(cd backend && grep -rlwE "$padrao" --include='test_*.py' tests comum/tests integracoes 2>/dev/null | sort); do
      alvos="$alvos $t"
    done
  fi
  for t in $arquivos; do
    alvos="$alvos $t"
  done
  # tira repetidos mantendo a ordem
  alvos=$(echo $alvos | tr ' ' '\n' | awk 'NF && !visto[$0]++' | tr '\n' ' ' | sed 's/ $//')
fi

if [ "$b_tudo" = "true" ]; then
  bt=tudo
elif [ -n "$alvos" ]; then
  bt=lista
else
  bt=nenhum
fi
if [ "$f_tudo" = "true" ]; then ft=tudo; else ft=alterados; fi

cat <<EOF
backend=$backend
frontend=$frontend
infra=$infra
backend_testes=$bt
backend_alvos=$alvos
frontend_testes=$ft
EOF
