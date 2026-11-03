#!/bin/sh
# T-427: confere a seleção de testes do CI com PRs de exemplo. Roda no job de infra.
set -eu
cd "$(git rev-parse --show-toplevel)"
falhas=0

# caso "descrição" "EVENTO" "BASE" "chave=valor esperado ..." -- arquivos...
caso() {
  desc=$1; ev=$2; base=$3; esperado=$4; shift 4
  saida=$(printf '%s\n' "$@" | EVENTO=$ev BASE=$base sh infra/scripts/selecionar-testes.sh)
  for par in $esperado; do
    if ! echo "$saida" | grep -qx "$par"; then
      echo "FALHOU: $desc: esperava $par"; echo "$saida"; falhas=$((falhas + 1)); break
    fi
  done
}
contem() { # contem "descrição" "trecho" -- arquivos...
  desc=$1; trecho=$2; shift 2
  if ! printf '%s\n' "$@" | sh infra/scripts/selecionar-testes.sh | grep '^backend_alvos=' | grep -q "$trecho"; then
    echo "FALHOU: $desc: alvos sem $trecho"; falhas=$((falhas + 1))
  fi
}

caso "só um app" pull_request develop "backend=true frontend=false backend_testes=lista frontend_testes=alterados" backend/apps/filiais/services.py
contem "só um app roda a pasta de testes dele" "apps/filiais/tests" backend/apps/filiais/services.py
caso "só frontend" pull_request develop "backend=false frontend=true backend_testes=nenhum frontend_testes=alterados" frontend/src/app/page.tsx
caso "só docs" pull_request develop "backend=false frontend=false infra=false" docs/regras-de-negocio.md tarefas/backlog.md
caso "config do backend" pull_request develop "backend_testes=tudo" backend/config/settings/base.py
caso "núcleo comum" pull_request develop "backend_testes=tudo" backend/comum/erros.py
caso "conftest" pull_request develop "backend_testes=tudo" backend/tests/aceitacao/conftest.py
caso "requirements" pull_request develop "backend_testes=tudo" backend/requirements.txt
caso "migração de app" pull_request develop "backend_testes=tudo" backend/apps/locacoes/migrations/0099_x.py
caso "openapi" pull_request develop "backend_testes=tudo frontend_testes=tudo" docs/api/openapi.yaml
caso "package.json" pull_request develop "frontend_testes=tudo" frontend/package.json
caso "config do vitest" pull_request develop "frontend_testes=tudo" frontend/vitest.config.ts
caso "fixtures do frontend" pull_request develop "frontend_testes=tudo" frontend/src/testes/api-falsa.ts
caso "só texto no backend" pull_request develop "backend=true backend_testes=nenhum" backend/apps/locacoes/README.md
caso "workflow" pull_request develop "backend_testes=tudo frontend_testes=tudo infra=true" .github/workflows/ci.yml
caso "push na develop" push develop "backend_testes=tudo frontend_testes=tudo infra=true" docs/x.md
caso "PR para a main" pull_request main "backend_testes=tudo frontend_testes=tudo" docs/x.md

if [ "$falhas" -gt 0 ]; then echo "$falhas caso(s) com falha"; exit 1; fi
echo "Seleção de testes do CI: todos os casos conferem"
