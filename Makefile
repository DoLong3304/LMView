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

# ─── Docker Swarm (AWS EC2 Multi-Node) ───────────────────────────────────────

.PHONY: swarm-deploy
swarm-deploy: ## Build images, push to local registry, and deploy Swarm stack
	bash scripts/deploy_aws_swarm.sh

.PHONY: swarm-deploy-quick
swarm-deploy-quick: ## Deploy Swarm stack (skip image build, push existing)
	bash scripts/deploy_aws_swarm.sh --skip-build

.PHONY: swarm-deploy-services
swarm-deploy-services: ## Targeted deploy specific services. Usage: make swarm-deploy-services SVCS="fastapi-prod,ai-service"
	@if [ -z "$(SVCS)" ]; then echo "Usage: make swarm-deploy-services SVCS=\"svc1,svc2\""; exit 1; fi
	bash scripts/deploy_aws_swarm.sh --services="$(SVCS)"

.PHONY: swarm-push
swarm-push: ## Build and push images to local registry only (no deploy)
	bash scripts/deploy_aws_swarm.sh --registry-only

.PHONY: swarm-status
swarm-status: ## Show Swarm services, tasks, and node health
	@echo "═══ Swarm Nodes ═══"
	@docker node ls 2>/dev/null || echo "  Not in Swarm mode."
	@echo ""
	@echo "═══ Stack Services ═══"
	@docker stack services lmview 2>/dev/null || echo "  Stack 'lmview' not deployed."
	@echo ""
	@echo "═══ Running Tasks ═══"
	@docker stack ps lmview --filter "desired-state=running" \
		--format "table {{.Name}}\t{{.Node}}\t{{.CurrentState}}\t{{.Error}}" 2>/dev/null | head -50 || true
	@echo ""
	@echo "═══ Failed Tasks (last 10) ═══"
	@docker stack ps lmview --filter "desired-state=shutdown" \
		--format "table {{.Name}}\t{{.Node}}\t{{.CurrentState}}\t{{.Error}}" 2>/dev/null | head -11 || true

.PHONY: swarm-logs
swarm-logs: ## Tail logs for a Swarm service (usage: make swarm-logs SVC=fastapi-prod)
	@if [ -z "$(SVC)" ]; then \
		echo "Usage: make swarm-logs SVC=<service-name>"; \
		echo "Available services:"; \
		docker stack services lmview --format '  {{.Name}}' 2>/dev/null | sed "s/lmview_//" || true; \
	else \
		docker service logs lmview_$(SVC) --tail 50 -f; \
	fi

.PHONY: swarm-restart
swarm-restart: ## Rolling restart a Swarm service (usage: make swarm-restart SVC=fastapi-prod)
	@if [ -z "$(SVC)" ]; then \
		echo "Usage: make swarm-restart SVC=<service-name>"; \
	else \
		docker service update --force lmview_$(SVC); \
	fi

.PHONY: swarm-down
swarm-down: ## Remove the Swarm stack (keeps registry and volumes)
	docker stack rm lmview


# ─── Jobs ────────────────────────────────────────────────────────────────────

.PHONY: submit-jobs
submit-jobs: ## Submit Flink streaming job
	bash scripts/submit_flink_job.sh

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

.PHONY: docs-version
docs-version: ## Show current docs version
	@echo "Version is set in VERSION: $$(cat VERSION 2>/dev/null || echo 'unknown')"

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
