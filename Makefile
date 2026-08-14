.PHONY: help front-build static-copy back-run back-run-dev test test-unit test-integration lint lint-frontend lint-python typecheck docker-build docker-up docker-down clean-static

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## $$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

front-build: ## Build Vue 3 frontend and copy to backend/static
	bash scripts/copy_front_to_static.sh

static-copy: ## Copy existing frontend/dist -> backend/static (no rebuild)
	SKIP_BUILD=1 bash scripts/copy_front_to_static.sh

back-run: ## Start FastAPI backend on port 8001
	python main.py api --port 8001

back-run-dev: ## Start FastAPI backend with --reload (dev only)
	python main.py api --port 8001 --reload

test: ## Run all backend tests
	python -m pytest tests/ -x

test-unit: ## Run unit tests (excludes integration, slow, missing_greenlet markers)
	python -m pytest tests/ -m "not slow and not missing_greenlet and not integration" -x

test-integration: ## Run integration tests only
	python -m pytest tests/ -m integration -v --timeout=120

lint-frontend: ## Lint frontend with eslint (no fix)
	cd frontend && npx eslint . --ext .vue,.js,.jsx,.cjs,.mjs --ignore-pattern node_modules,.git,dist,.output

lint-python: ## Lint backend with ruff
	ruff check .

lint: lint-frontend lint-python ## Lint frontend + backend

typecheck: ## Frontend TypeScript type check (vue-tsc)
	cd frontend && npm run typecheck

docker-build: ## Build production Docker image
	docker build -t bikemaster .

docker-up: ## Start Docker compose stack
	docker compose up -d

docker-down: ## Stop Docker compose stack
	docker compose down

clean-static: ## Remove generated static assets (index.html, sw.js, assets/, sqlite3/)
	rm -f bike_analyzer/backend/static/index.html bike_analyzer/backend/static/sw.js
	rm -rf bike_analyzer/backend/static/assets bike_analyzer/backend/static/sqlite3
