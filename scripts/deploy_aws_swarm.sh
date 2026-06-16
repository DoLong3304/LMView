#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# deploy_aws_swarm.sh — Deploy LMView to a Docker Swarm cluster on AWS EC2
# ─────────────────────────────────────────────────────────────────────────────
# Prerequisites:
#   1. Docker Swarm initialized:  docker swarm init --advertise-addr <PRIVATE_IP>
#   2. Worker joined:             docker swarm join --token <TOKEN> <MANAGER_IP>:2377
#   3. Node labels applied:
#        docker node update --label-add role=core  <manager-node-id>
#        docker node update --label-add role=worker <worker-node-id>
#   4. Shared EFS mounted at /mnt/efs/lmview on both nodes
#   5. .env file populated with production secrets
#
# Usage:
#   bash scripts/deploy_aws_swarm.sh [--build] [--skip-build]
#
# Options:
#   --build       Force rebuild all images before deploy (default)
#   --skip-build  Skip image build, deploy with existing images
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# ── Color helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { printf "${CYAN}[deploy]${NC} %s\n" "$*"; }
ok()   { printf "${GREEN}[deploy]${NC} ✅ %s\n" "$*"; }
warn() { printf "${YELLOW}[deploy]${NC} ⚠️  %s\n" "$*"; }
err()  { printf "${RED}[deploy]${NC} ❌ %s\n" "$*" >&2; exit 1; }

STACK_NAME="lmview"
DO_BUILD=true

# ── Parse arguments ──────────────────────────────────────────────────────────
for arg in "$@"; do
  case "$arg" in
    --skip-build) DO_BUILD=false ;;
    --build)      DO_BUILD=true ;;
    *)            warn "Unknown argument: $arg" ;;
  esac
done

# ── Preflight checks ────────────────────────────────────────────────────────
log "Running preflight checks..."

command -v docker >/dev/null 2>&1 || err "docker is not installed or not in PATH."

# Verify swarm mode
if ! docker info --format '{{.Swarm.LocalNodeState}}' 2>/dev/null | grep -q "active"; then
  err "Docker Swarm is not active. Run: docker swarm init --advertise-addr <PRIVATE_IP>"
fi

# Verify .env exists
if [ ! -f .env ]; then
  err ".env file not found. Copy .env.example and configure production values."
fi

# Verify compose files exist
[ -f docker-compose.yml ]       || err "docker-compose.yml not found."
[ -f docker-compose.swarm.yml ] || err "docker-compose.swarm.yml not found."

# Verify node labels
CORE_NODES=$(docker node ls --filter "node.label.role=core" --format '{{.Hostname}}' 2>/dev/null | wc -l)
WORKER_NODES=$(docker node ls --filter "node.label.role=worker" --format '{{.Hostname}}' 2>/dev/null | wc -l)

if [ "$CORE_NODES" -eq 0 ]; then
  warn "No nodes with label role=core found. Run: docker node update --label-add role=core <node-id>"
fi
if [ "$WORKER_NODES" -eq 0 ]; then
  warn "No nodes with label role=worker found. Run: docker node update --label-add role=worker <node-id>"
fi

ok "Preflight checks passed (core=$CORE_NODES, worker=$WORKER_NODES nodes)"

# ── Build images locally ────────────────────────────────────────────────────
if [ "$DO_BUILD" = true ]; then
  log "Building images locally (prod profile)..."
  docker compose --profile prod --profile monitoring --profile logging build
  ok "Images built successfully."
else
  log "Skipping image build (--skip-build)."
fi

# ── Deploy the stack ─────────────────────────────────────────────────────────
log "Deploying stack '$STACK_NAME'..."
docker stack deploy \
  -c docker-compose.yml \
  -c docker-compose.swarm.yml \
  "$STACK_NAME" \
  --resolve-image never

ok "Stack '$STACK_NAME' deployed."

# ── Post-deployment status ───────────────────────────────────────────────────
log "Waiting 10s for services to start..."
sleep 10

echo ""
log "Service status:"
docker stack services "$STACK_NAME"

echo ""
log "Stack tasks (non-running):"
docker stack ps "$STACK_NAME" --filter "desired-state=running" --format "table {{.Name}}\t{{.Node}}\t{{.CurrentState}}" | head -50

echo ""
ok "Deployment complete!"
echo ""
log "Next steps:"
echo "  1. Verify all services are running:  docker stack services $STACK_NAME"
echo "  2. Check service logs:               docker service logs ${STACK_NAME}_fastapi-prod"
echo "  3. Monitor node status:              docker node ls"
echo "  4. Access the app at:                https://\${CERTBOT_DOMAIN}"
echo ""
warn "Ensure AWS Security Groups allow:"
echo "  - TCP 2377  (Swarm management)     — between nodes"
echo "  - TCP 7946  (Swarm gossip)         — between nodes"
echo "  - UDP 7946  (Swarm gossip)         — between nodes"
echo "  - UDP 4789  (VXLAN overlay)        — between nodes"
echo "  - TCP 80    (HTTP)                 — public"
echo "  - TCP 443   (HTTPS)                — public"
echo "  - TCP 8080  (FastAPI, optional)    — internal/admin"
