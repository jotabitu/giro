# PostgreSQL 16 da produção com pgBackRest (T-373, ADR 0033, opção B). O compose de produção
# liga o arquivamento de WAL (archive_command) ao pgBackRest; o repositório (bucket cifrado de
# outro provedor) vem por PGBACKREST_* no ambiente do contêiner, sem arquivo de configuração.
FROM postgres:16

RUN apt-get update && apt-get install -y --no-install-recommends pgbackrest \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/log/pgbackrest /var/spool/pgbackrest /tmp/pgbackrest \
    && chown -R postgres:postgres /var/log/pgbackrest /var/spool/pgbackrest /tmp/pgbackrest
