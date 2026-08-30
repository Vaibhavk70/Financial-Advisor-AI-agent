.PHONY: help up down logs build clean test migrate lint setup monitoring-up

# Colors for pretty terminal output
CYAN  = \033[36m
GREEN = \033[32m
RESET = \033[0m

help: ## Show available developer commands
	@echo ""
	@echo "  $(CYAN)AI Financial Advisor — Developer Commands$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""

# ─── Docker Compose Commands ──────────────────────────────────────────
up: ## Start all services in background
	docker compose up -d
	@echo "$(GREEN)✅ All services running! Visit http://localhost$(RESET)"

up-build: ## Rebuild images and start services
	docker compose up -d --build

down: ## Stop all running services
	docker compose down

restart: ## Restart all services
	docker compose restart

logs: ## View logs from all services
	docker compose logs -f

logs-auth: ## View logs from auth-service only
	docker compose logs -f auth-service

build: ## Build all Docker images
	docker compose build

# ─── Database Migration Commands ──────────────────────────────────────
migrate: ## Run database migrations (alembic upgrade head)
	docker compose run --rm auth-service alembic upgrade head

migrate-rollback: ## Rollback last database migration
	docker compose run --rm auth-service alembic downgrade -1

# ─── Testing & Code Quality Commands ─────────────────────────────────
test: ## Run unit and integration tests
	docker compose run --rm auth-service pytest tests/ -v --cov=app

lint: ## Run code linter (ruff)
	ruff check ./services

format: ## Format code with black
	black ./services

# ─── Setup & Utility Commands ─────────────────────────────────────────
monitoring-up: ## Start Prometheus and Grafana monitoring dashboard
	docker compose --profile monitoring up -d prometheus grafana
	@echo "$(GREEN)Grafana Dashboard: http://localhost:3001 (admin/admin)$(RESET)"

setup: ## First-time setup: create .env, start containers, run DB migrations
	@test -f .env || (cp .env.example .env && echo "$(GREEN)✅ Created .env from template$(RESET)")
	$(MAKE) up
	@sleep 5
	$(MAKE) migrate
	@echo "$(GREEN)✅ Setup complete! Visit http://localhost:8001/docs$(RESET)"

clean: ## Remove containers, volumes, and temporary files
	docker compose down -v --remove-orphans
	docker system prune -f