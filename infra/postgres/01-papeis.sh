#!/bin/sh
# Cria os papéis de banco da ADR 0016. Roda uma vez, na criação do volume do Postgres
# (docker-entrypoint-initdb.d), como o superusuário POSTGRES_USER. Em homologação e produção
# o mesmo SQL se aplica ao banco gerenciado, com as senhas do cofre (infra/README.md).
#
#   giro_migracao  dono dos schemas e tabelas; migrate_schemas e criação de schema de empresa
#   giro_app       atende requisições e Celery; sem DDL; auditoria só SELECT e INSERT
#   giro_expurgo   dono da função auditoria_expurgar (SECURITY DEFINER); sem login
#
# Os GRANT por schema (inclusive o REVOKE na auditoria) são do backend, na rotina que cria o schema.
set -e

: "${POSTGRES_PASSWORD_MIGRACAO:?defina POSTGRES_PASSWORD_MIGRACAO}"
: "${POSTGRES_PASSWORD_APP:?defina POSTGRES_PASSWORD_APP}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v senha_migracao="$POSTGRES_PASSWORD_MIGRACAO" -v senha_app="$POSTGRES_PASSWORD_APP" <<'SQL'
SELECT 'CREATE ROLE giro_migracao LOGIN NOSUPERUSER NOCREATEROLE'
  WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'giro_migracao') \gexec
SELECT 'CREATE ROLE giro_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE'
  WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'giro_app') \gexec
SELECT 'CREATE ROLE giro_expurgo NOLOGIN NOSUPERUSER'
  WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'giro_expurgo') \gexec

ALTER ROLE giro_migracao PASSWORD :'senha_migracao';
ALTER ROLE giro_app PASSWORD :'senha_app';

-- O post_migrate roda como giro_migracao e passa a função auditoria_expurgar para giro_expurgo
-- (ALTER FUNCTION ... OWNER TO), o que exige ser membro do papel (T-034, T-052).
GRANT giro_expurgo TO giro_migracao;

-- giro_migracao cria schemas e é dono do que criar.
GRANT CONNECT, CREATE ON DATABASE :"DBNAME" TO giro_migracao;
GRANT CONNECT ON DATABASE :"DBNAME" TO giro_app, giro_expurgo;

-- Schema public (plataforma): dono giro_migracao; giro_app usa sem criar.
ALTER SCHEMA public OWNER TO giro_migracao;
GRANT USAGE ON SCHEMA public TO giro_app, giro_expurgo;
ALTER DEFAULT PRIVILEGES FOR ROLE giro_migracao IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO giro_app;
ALTER DEFAULT PRIVILEGES FOR ROLE giro_migracao IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO giro_app;
SQL
