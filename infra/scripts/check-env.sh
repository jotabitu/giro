#!/bin/sh
# Falha se o docker-compose.yml usar uma variável ${VAR} que não está no .env.example.
set -e
cd "$(dirname "$0")/../.."

faltando=""
for v in $(grep -o '\${[A-Z_][A-Z0-9_]*' docker-compose.yml | sed 's/\${//' | sort -u); do
  grep -q "^$v=" .env.example || faltando="$faltando $v"
done

if [ -n "$faltando" ]; then
  echo "Variáveis usadas no docker-compose.yml e ausentes de .env.example:$faltando"
  exit 1
fi
echo ".env.example cobre todas as variáveis do docker-compose.yml"
