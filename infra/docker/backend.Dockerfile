# Imagem do backend, do worker Celery e do beat (mesma imagem, comandos diferentes no Compose).
# Contrato com o backend: ver infra/README.md, seção "O que o backend precisa respeitar".
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# libpq (psycopg), WeasyPrint (pango), fontes para PDF, cliente do Postgres para pg_isready.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev postgresql-client \
        libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libffi-dev libjpeg-dev \
        shared-mime-info fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependências primeiro, para o cache de camadas sobreviver a mudanças de código.
COPY backend/requirements.txt backend/requirements-dev.txt ./
RUN pip install -r requirements-dev.txt

# O código entra por bind mount no Compose (./backend:/app); a cópia vale para uso sem mount.
COPY backend/ ./

COPY infra/docker/backend-entrypoint.sh /usr/local/bin/backend-entrypoint.sh
RUN chmod +x /usr/local/bin/backend-entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["backend-entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
