VENV   := .venv
PYTHON := $(VENV)/bin/python
PIP    := uv pip

.PHONY: venv install install-dev run test lint lint-fix format check

venv:
	uv venv

install: venv
	$(PIP) install -e .

install-dev: venv
	$(PIP) install -e ".[dev]"

run:
	$(VENV)/bin/uvicorn main:app --reload --port 8000

test:
	$(PYTHON) -m pytest tests/ -v --tb=short

lint:
	$(PYTHON) -m ruff check .

lint-fix:
	$(PYTHON) -m ruff check --fix .

format:
	$(PYTHON) -m ruff format .

check: lint
	$(PYTHON) -m ruff format --check .
