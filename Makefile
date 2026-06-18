.PHONY: venv install install-dev run test lint format check lint-fix \
       frontend-install frontend-dev dev

# Backend targets
venv:
	cd backend && $(MAKE) venv

install:
	cd backend && $(MAKE) install

install-dev:
	cd backend && $(MAKE) install-dev

run:
	cd backend && $(MAKE) run

test:
	cd backend && $(MAKE) test

lint:
	cd backend && $(MAKE) lint

format:
	cd backend && $(MAKE) format

lint-fix:
	cd backend && $(MAKE) lint-fix

check:
	cd backend && $(MAKE) check

# Frontend targets
frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

# Run both backend and frontend together
dev:
	@echo "Starting backend on :8000 and frontend on :5173..."
	@cd backend && $(MAKE) run &
	@cd frontend && npm run dev
