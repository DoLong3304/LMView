# ─────────────────────────────────────────────────────────────────────────────
# Makefile — convenience targets for development and production workflows
# ─────────────────────────────────────────────────────────────────────────────
.DEFAULT_GOAL := help

# ─── Profile-Based Startup (Recommended) ─────────────────────────────────────

.PHONY: core
core: ## Start ONLY core services (17GB RAM) - Default for daily dev
	@echo "🚀 Starting CORE services (17GB RAM)..."
	docker compose -f docker-compose.core.yml up -d
	@echo "✅ Core services started!"
	@echo "   Frontend: http://localhost"
	@echo "   FastAPI:  http://localhost:8080"
	@echo "   Flink UI: http://localhost:8081"

.PHONY: monitoring
monitoring: core ## Start core + monitoring stack (18GB RAM) - For performance monitoring
	@echo "📊 Starting MONITORING stack (18GB RAM total)..."
	docker compose -f docker-compose.monitoring.yml up -d
	@echo "✅ Monitoring started!"
	@echo "   Grafana:    http://localhost:3001 (admin/admin)"
	@echo "   Prometheus: http://localhost:9090"

.PHONY: logs
logs: monitoring ## Start core + monitoring + logs (18.8GB RAM) - For debugging
	@echo "📝 Starting LOGGING stack (18.8GB RAM total)..."
	docker compose -f docker-compose.elk.yml up -d
	@echo "✅ Logging started!"
	@echo "   Loki API: http://localhost:3100"
	@echo "   Logs in Grafana: http://localhost:3001 → Centralized Logs dashboard"

.PHONY: full
full: logs ## Start ALL services (alias for 'logs')

.PHONY: stop-logs
stop-logs: ## Stop logging stack
	@echo "🛑 Stopping LOGGING stack..."
	docker compose -f docker-compose.elk.yml down
	@echo "✅ Logging stopped"

.PHONY: stop-monitoring
stop-monitoring: ## Stop monitoring stack
	@echo "🛑 Stopping MONITORING stack..."
	docker compose -f docker-compose.monitoring.yml down
	@echo "✅ Monitoring stopped"

.PHONY: stop-core
stop-core: ## Stop core services
	@echo "🛑 Stopping CORE services..."
	docker compose -f docker-compose.core.yml down
	@echo "✅ Core stopped"

.PHONY: stop-all
stop-all: stop-logs stop-monitoring stop-core ## Stop ALL services

.PHONY: restart-core
restart-core: ## Restart core services
	@echo "🔄 Restarting CORE services..."
	docker compose -f docker-compose.core.yml restart
	@echo "✅ Core restarted"

# ─── Development (Legacy - uses old docker-compose.yml) ──────────────────────

.PHONY: dev
dev: ## [LEGACY] Start all services in development mode (hot-reload, no SSL)
	docker compose up -d

.PHONY: dev-build
dev-build: ## [LEGACY] Rebuild and start in development mode
	docker compose up -d --build

.PHONY: dev-logs
dev-logs: ## Tail logs for all services
	docker compose logs -f

.PHONY: dev-down
dev-down: ## [LEGACY] Stop all development services
	docker compose down

# ─── Production ──────────────────────────────────────────────────────────────

.PHONY: prod
prod: ## Start all services in production mode (SSL, multi-worker)
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

.PHONY: prod-build
prod-build: ## Rebuild and start in production mode
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

.PHONY: prod-down
prod-down: ## Stop all production services
	docker compose -f docker-compose.yml -f docker-compose.prod.yml down

# ─── Jobs ────────────────────────────────────────────────────────────────────

.PHONY: submit-jobs
submit-jobs: ## Submit Flink and Spark streaming jobs
	bash scripts/auto_submit_jobs.sh

# ─── Testing ─────────────────────────────────────────────────────────────────

.PHONY: test
test: ## Run unit and integration tests
	PYTHONPATH=. python -m pytest tests/ -m "unit or integration" -v

.PHONY: test-all
test-all: ## Run all tests including e2e (requires running services)
	PYTHONPATH=. python -m pytest tests/ -v

.PHONY: test-cov
test-cov: ## Run tests with coverage report
	PYTHONPATH=. python -m pytest tests/ -m "unit or integration" --cov=backend --cov-report=term-missing

# ─── Utilities ───────────────────────────────────────────────────────────────

.PHONY: status
status: ## Show status and RAM usage of all containers
	@echo "📊 Container Status:"
	@docker compose -f docker-compose.core.yml ps 2>/dev/null || true
	@docker compose -f docker-compose.monitoring.yml ps 2>/dev/null || true
	@docker compose -f docker-compose.elk.yml ps 2>/dev/null || true
	@echo ""
	@echo "💾 RAM Usage (Top 20):"
	@docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | head -20

.PHONY: clean
clean: ## Remove all containers, volumes, and networks (DANGEROUS)
	@echo "⚠️  WARNING: This will remove ALL containers and volumes!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker compose -f docker-compose.elk.yml down -v 2>/dev/null || true; \
		docker compose -f docker-compose.monitoring.yml down -v 2>/dev/null || true; \
		docker compose -f docker-compose.core.yml down -v 2>/dev/null || true; \
		docker compose down -v --remove-orphans 2>/dev/null || true; \
		echo "✅ All services and volumes removed"; \
	else \
		echo "❌ Cancelled"; \
	fi

.PHONY: help
help: ## Show this help
	@echo "Lambda Architecture - Docker Compose Profiles"
	@echo ""
	@echo "📦 Profile-Based Startup (Recommended):"
	@echo "  make core              Start ONLY core services (17GB RAM) - Daily dev"
	@echo "  make monitoring        Start core + monitoring (18GB RAM) - Performance"
	@echo "  make logs              Start core + monitoring + logs (18.8GB RAM) - Debug"
	@echo "  make full              Start ALL services (alias for 'logs')"
	@echo ""
	@echo "🛑 Stop Services:"
	@echo "  make stop-logs         Stop logging stack"
	@echo "  make stop-monitoring   Stop monitoring stack"
	@echo "  make stop-core         Stop core services"
	@echo "  make stop-all          Stop ALL services"
	@echo ""
	@echo "🔧 Other Commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -v "Profile-Based\|Stop Services" | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

