SHELL := /bin/bash
COMPOSE := docker compose -f docker-compose.local.yml
PYTHON := .venv/bin/python
PIP := .venv/bin/pip

.PHONY: setup start start-bg stop logs status health test clean-test

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

test: $(PYTHON)
	$(PYTHON) -m compileall -q app scripts
	APP_ENV=development $(PYTHON) -m scripts.preflight
	@if command -v node >/dev/null 2>&1; then node --check static/app.js; else echo "node not installed: JS syntax check skipped locally (CI still checks it)"; fi
	$(PYTHON) -m pytest -q

clean-test:
	rm -rf .venv /tmp/mb16-test.db /tmp/mb16-test-uploads
