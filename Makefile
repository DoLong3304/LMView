# ─────────────────────────────────────────────────────────────────────────────
# Makefile — convenience targets for development and production workflows
# ─────────────────────────────────────────────────────────────────────────────
.DEFAULT_GOAL := help

# ─── Development ─────────────────────────────────────────────────────────────

.PHONY: dev
dev: ## Start core services in dev mode (hot-reload, localhost CORS)
	@echo "🚀 Starting DEV services..."
	docker compose --profile dev up -d
	@echo "✅ Dev services started!"
	@echo "   Frontend: http://localhost"
	@echo "   FastAPI:  http://localhost:8080"
	@echo "   Flink UI: http://localhost:8081"

.PHONY: dev-build
dev-build: ## Rebuild and start in development mode
	docker compose --profile dev up -d --build

.PHONY: dev-logs
dev-logs: ## Tail logs for all running services
	docker compose logs -f

.PHONY: dev-down
dev-down: ## Stop all development services
	docker compose --profile dev down

# ─── Monitoring & Logging (opt-in stacks) ────────────────────────────────────

.PHONY: monitoring
monitoring: ## Start monitoring stack (Prometheus, Grafana, exporters)
	@echo "📊 Starting MONITORING stack..."
	docker compose --profile dev --profile monitoring up -d
	@echo "✅ Monitoring started!"
	@echo "   Grafana:    http://localhost:3001 (admin/admin)"
	@echo "   Prometheus: http://localhost:9090"

.PHONY: logging
logging: ## Start logging stack (Loki, Promtail)
	@echo "📝 Starting LOGGING stack..."
	docker compose --profile dev --profile monitoring --profile logging up -d
	@echo "✅ Logging started!"
	@echo "   Loki API: http://localhost:3100"
	@echo "   Logs in Grafana: http://localhost:3001 → Centralized Logs dashboard"

.PHONY: stop-logging
stop-logging: ## Stop logging stack
	@echo "🛑 Stopping LOGGING stack..."
	docker compose --profile logging stop loki promtail
	@echo "✅ Logging stopped"

.PHONY: stop-monitoring
stop-monitoring: ## Stop monitoring stack
	@echo "🛑 Stopping MONITORING stack..."
	docker compose --profile monitoring stop prometheus grafana kafka-exporter node-exporter
	@echo "✅ Monitoring stopped"

# ─── Production ──────────────────────────────────────────────────────────────

.PHONY: prod
prod: ## Start all services in production mode (SSL, multi-worker, domain CORS)
	@echo "🚀 Starting PROD services..."
	docker compose --profile prod --profile monitoring --profile logging up -d
	@echo "✅ Production started!"

.PHONY: prod-build
prod-build: ## Rebuild and start in production mode
	docker compose --profile prod --profile monitoring --profile logging up -d --build

.PHONY: prod-down
prod-down: ## Stop all production services
	docker compose --profile prod --profile monitoring --profile logging down

# ─── Stop All ────────────────────────────────────────────────────────────────

.PHONY: stop-all
stop-all: ## Stop ALL services across all profiles
	@echo "🛑 Stopping ALL services..."
	docker compose --profile dev --profile prod --profile monitoring --profile logging down
	@echo "✅ All stopped"

# ─── Docker Swarm (AWS EC2) ──────────────────────────────────────────────────

.PHONY: swarm-deploy
swarm-deploy: ## Deploy to Docker Swarm (builds images, then deploys stack)
	bash scripts/deploy_aws_swarm.sh

.PHONY: swarm-deploy-quick
swarm-deploy-quick: ## Deploy to Docker Swarm (skip image build)
	bash scripts/deploy_aws_swarm.sh --skip-build

.PHONY: swarm-status
swarm-status: ## Show Swarm stack services and tasks
	@docker stack services lmview 2>/dev/null || echo "Stack 'lmview' not deployed."
	@echo ""
	@docker stack ps lmview --format "table {{.Name}}\t{{.Node}}\t{{.CurrentState}}" 2>/dev/null | head -40 || true

.PHONY: swarm-down
swarm-down: ## Remove the Swarm stack
	docker stack rm lmview

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
	@docker compose ps 2>/dev/null || true
	@echo ""
	@echo "💾 RAM Usage (Top 20):"
	@docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | head -20

.PHONY: clean
clean: ## Remove all containers, volumes, and networks (DANGEROUS)
	@echo "⚠️  WARNING: This will remove ALL containers and volumes!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker compose --profile dev --profile prod --profile monitoring --profile logging down -v --remove-orphans; \
		echo "✅ All services and volumes removed"; \
	else \
		echo "❌ Cancelled"; \
	fi

.PHONY: help
help: ## Show this help
	@echo "LMView — Docker Compose Targets"
	@echo ""
	@echo "🔧 Development:"
	@echo "  make dev               Start core services in dev mode"
	@echo "  make dev-build         Rebuild and start dev"
	@echo "  make dev-logs          Tail logs"
	@echo "  make dev-down          Stop dev services"
	@echo ""
	@echo "📊 Monitoring & Logging (opt-in):"
	@echo "  make monitoring        Start dev + monitoring stack"
	@echo "  make logging           Start dev + monitoring + logging stack"
	@echo "  make stop-monitoring   Stop monitoring stack"
	@echo "  make stop-logging      Stop logging stack"
	@echo ""
	@echo "🚀 Production:"
	@echo "  make prod              Start all services in prod mode"
	@echo "  make prod-build        Rebuild and start prod"
	@echo "  make prod-down         Stop prod services"
	@echo ""
	@echo "🛑 Stop:"
	@echo "  make stop-all          Stop ALL services across all profiles"
	@echo ""
	@echo "🔧 Other:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		grep -v "dev\b\|dev-build\|dev-logs\|dev-down\|monitoring\b\|logging\b\|stop-monitoring\|stop-logging\|prod\b\|prod-build\|prod-down\|stop-all" | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
