# Imagem de desenvolvimento do frontend. Contrato: infra/README.md.
FROM node:22-bookworm-slim

ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /app

# Dependências primeiro, para o cache de camadas. O código entra por bind mount.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./

EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0", "--port", "3000"]
