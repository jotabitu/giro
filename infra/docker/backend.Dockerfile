# Imagem do backend, do worker Celery e do beat (mesma imagem, comandos diferentes no Compose).
# Dois alvos (ADR 0027): `producao` (homologação e produção) e `dev` (docker-compose.yml).
# Contrato com o backend: ver infra/README.md, seção "O que o backend precisa respeitar".
# Sem --target, a imagem é a última etapa, `dev`: homologação e produção sempre pedem `producao`.
FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Só o que roda: WeasyPrint (pango), fontes para PDF, cliente do Postgres para pg_isready.
RUN apt-get update && apt-get install -y --no-install-recommends \
        postgresql-client libpq5 \
        libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libharfbuzz-subset0 \
        shared-mime-info fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY infra/docker/backend-entrypoint.sh /usr/local/bin/backend-entrypoint.sh
RUN chmod +x /usr/local/bin/backend-entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["backend-entrypoint.sh"]


# --- Homologação e produção: só requirements.txt, sem root, Gunicorn como processo 1 ---
FROM base AS producao

# Dependências primeiro, para o cache de camadas sobreviver a mudanças de código.
COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

# Usuário sem root; o HOME existe porque o WeasyPrint e o Pillow guardam cache nele.
RUN useradd --system --uid 10001 --create-home --home-dir /home/giro giro \
    && chown giro:giro /app
COPY --chown=giro:giro backend/ ./
COPY --chown=giro:giro infra/docker/gunicorn.conf.py /app/gunicorn.conf.py
USER giro

# Estáticos do Admin da plataforma: o proxy os serve (infra/deploy/docker-compose.homologacao.yml).
# O collectstatic não abre o banco; a chave e a URL abaixo valem só para este comando.
RUN DJANGO_SETTINGS_MODULE=config.settings.dev DJANGO_SECRET_KEY=so-para-o-collectstatic \
    DATABASE_URL=postgres://x:x@localhost/x \
    python manage.py collectstatic --noinput

# Worker e beat usam esta imagem com o comando deles.
CMD ["gunicorn", "-c", "/app/gunicorn.conf.py", "config.wsgi:application"]


# --- Desenvolvimento: requirements-dev, root, runserver com o código por bind mount ---
FROM base AS dev

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev libffi-dev libjpeg-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/requirements-dev.txt ./
RUN pip install -r requirements-dev.txt

# O código entra por bind mount no Compose (./backend:/app); a cópia vale para uso sem mount.
COPY backend/ ./

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
