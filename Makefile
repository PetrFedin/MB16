SHELL := /bin/bash
COMPOSE := docker compose -f docker-compose.local.yml
PYTHON := .venv/bin/python
PIP := .venv/bin/pip
TEST_DB := sqlite:////tmp/mb16-test.db

.PHONY: setup start start-bg stop logs status health migrate migration-check test clean-test

setup:
	@test -f .env || (cp .env.example .env && echo "Created .env from .env.example")
	@docker compose version >/dev/null

start: setup
	$(COMPOSE) up --build

start-bg: setup
	$(COMPOSE) up --build -d
	@echo "MB16: http://localhost:8000/?debug_user=1001"
	@echo "Admin: http://localhost:8000/?debug_user=9001"

stop:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f app

status:
	$(COMPOSE) ps

health:
	@curl --fail --silent http://localhost:8000/health && echo

$(PYTHON):
	python3 -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt

migrate: $(PYTHON)
	$(PYTHON) -m alembic upgrade head

migration-check: $(PYTHON)
	$(PYTHON) -m alembic check

test: $(PYTHON)
	$(PYTHON) -m compileall -q app scripts migrations
	APP_ENV=development $(PYTHON) -m scripts.preflight
	@if command -v node >/dev/null 2>&1; then node --check static/app.js; else echo "node not installed: JS syntax check skipped locally (CI still checks it)"; fi
	rm -f /tmp/mb16-test.db
	DATABASE_URL=$(TEST_DB) APP_ENV=development STORAGE_BACKEND=local UPLOAD_DIR=/tmp/mb16-test-uploads $(PYTHON) -m alembic upgrade head
	TEST_DATABASE_URL=$(TEST_DB) $(PYTHON) -m pytest -q

clean-test:
	rm -rf .venv /tmp/mb16-test.db /tmp/mb16-test-uploads /tmp/mb16-browser.db /tmp/mb16-browser-uploads /tmp/mb16-resilience-uploads
