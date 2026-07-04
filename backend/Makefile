VENV   := .venv
PYTHON := $(VENV)/bin/python
PIP    := uv pip
MODEL  := pose_landmarker_lite.task
MODEL_URL := https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task

.PHONY: venv install install-dev run test lint lint-fix format check

venv:
	uv venv

$(MODEL):
	curl -L -o $(MODEL) $(MODEL_URL)

install: venv $(MODEL)
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
