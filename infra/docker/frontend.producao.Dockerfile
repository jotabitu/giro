# Imagem de produção do frontend (T-373, ADR 0027 e 0033): Next em `output: standalone`, sem root.
# O proxy manda /api/ direto ao Django; o Next só atende as telas. Contrato: infra/README.md.
FROM node:22-bookworm-slim AS construir
ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# Lido no build pelo next.config.ts; em produção o proxy não usa essa rota.
ARG API_URL_INTERNA=http://backend:8000
ENV API_URL_INTERNA=$API_URL_INTERNA
# O cliente tipado nao vai para o git: sai do OpenAPI (scripts/gerar-api.mjs le ../../docs/api).
COPY docs/api/openapi.yaml /docs/api/openapi.yaml
RUN npm run api:gerar && npm run build

FROM node:22-bookworm-slim AS producao
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000
WORKDIR /app
RUN useradd --system --uid 10001 --create-home giro
COPY --from=construir --chown=giro:giro /app/.next/standalone ./
COPY --from=construir --chown=giro:giro /app/.next/static ./.next/static
COPY --from=construir --chown=giro:giro /app/public ./public
USER giro
EXPOSE 3000
CMD ["node", "server.js"]
