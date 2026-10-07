# Alvos do dia a dia. Precisa de Docker com Compose v2 e make.
# No Windows rode pelo Git Bash ou WSL (make não vem no Windows por padrão).

COMPOSE := docker compose
BACKEND_RUN := $(COMPOSE) run --rm --no-deps backend
FRONTEND_RUN := $(COMPOSE) run --rm --no-deps frontend

.PHONY: help up down logs ps check infra-check backend-check frontend-check seed migrate shell api-schema api-client

help:
	@echo "make up              sobe tudo (Postgres, Redis, backend, worker, beat, frontend)"
	@echo "make down            para tudo (make down V=1 apaga também os volumes)"
	@echo "make check           infra + backend + frontend"
	@echo "make seed            carrega a empresa Moto Rápida"
	@echo "make migrate         migrate_schemas em todos os schemas"
	@echo "make api-schema      gera docs/api/openapi.yaml"
	@echo "make api-client      gera o cliente tipado do frontend"
	@echo "make logs / ps / shell"

.env:
	cp .env.example .env
	@echo ".env criado a partir de .env.example"

up: .env
	$(COMPOSE) up --build -d
	@echo "Frontend em http://localhost:3000 e API em http://localhost:8000/api/schema/ (portas em .env)"

down:
	$(COMPOSE) down $(if $(V),-v,)

logs:
	$(COMPOSE) logs -f --tail=100

ps:
	$(COMPOSE) ps

shell: .env
	$(COMPOSE) exec backend python manage.py shell

migrate: .env
	$(COMPOSE) exec backend python manage.py migrate_schemas --shared --noinput
	$(COMPOSE) exec backend python manage.py migrate_schemas --tenant --noinput

seed: .env
	$(COMPOSE) exec backend python manage.py seed_moto_rapida

api-schema: .env
	$(COMPOSE) exec backend python manage.py spectacular --file /tmp/openapi.yaml --validate
	$(COMPOSE) cp backend:/tmp/openapi.yaml docs/api/openapi.yaml

api-client: .env
	$(COMPOSE) exec frontend npm run api:gerar

check: infra-check backend-check frontend-check

infra-check: .env
	sh infra/scripts/check-env.sh
	$(COMPOSE) config --quiet

# Enquanto T-001 e T-002 não entregam, backend-check e frontend-check avisam e passam.
# Remover o desvio quando backend/manage.py e frontend/package.json existirem.
backend-check: .env
	@if [ ! -f backend/manage.py ]; then echo "AVISO: backend/manage.py não existe ainda (T-001); backend-check pulado"; else \
	  $(BACKEND_RUN) sh -c "ruff check . && ruff format --check . && mypy . && pytest -q"; fi

frontend-check: .env
	@if [ ! -f frontend/package.json ]; then echo "AVISO: frontend/package.json não existe ainda (T-002); frontend-check pulado"; else \
	  $(FRONTEND_RUN) sh -c "npm run lint && npm run typecheck && npm test -- --run && npm run build"; fi
