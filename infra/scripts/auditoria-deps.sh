#!/bin/sh
# Auditoria de dependências (T-361, M-04 da T-355): pip-audit no backend e npm audit no frontend.
# Falha com qualquer aviso do pip-audit (ele não separa por gravidade) e com aviso alto ou crítico
# do npm audit, salvo os de infra/auditoria/excecoes.txt (justificados, com validade).
# Uso: sh infra/scripts/auditoria-deps.sh [pip|npm]   (sem argumento, roda os dois)
# Precisa de pip-audit (pipx install pip-audit), node e npm no PATH.
set -e
cd "$(dirname "$0")/../.."

alvo=${1:-tudo}
falhou=0

if [ "$alvo" = tudo ] || [ "$alvo" = pip ]; then
  ignorar=""
  for id in $(node infra/scripts/auditoria-excecoes.mjs listar pip); do
    ignorar="$ignorar --ignore-vuln $id"
  done
  echo "== pip-audit (backend/requirements.txt)"
  # shellcheck disable=SC2086
  pip-audit -r backend/requirements.txt $ignorar || falhou=1
fi

if [ "$alvo" = tudo ] || [ "$alvo" = npm ]; then
  echo "== npm audit (frontend, sem devDependencies)"
  # O npm sai com 1 quando há aviso; quem decide é o filtro, que conhece as exceções.
  (cd frontend && npm audit --omit=dev --json || true) | node infra/scripts/auditoria-excecoes.mjs npm || falhou=1
fi

exit $falhou
