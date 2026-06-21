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
#   4. Shared EFS mounted at same path on both nodes
#   5. .env file populated with production secrets
#
# Usage:
#   bash scripts/deploy_aws_swarm.sh [--build] [--skip-build] [--registry-only]
#                                    [--registry-port=5000] [--no-color]
#
# Options:
#   --build                Force rebuild all images before deploy (default)
#   --skip-build           Skip image build, deploy with existing images
#   --registry-only        Just push images to the local registry, don't deploy
#   --registry-port=N      Override the local registry port (default 5000)
#   --no-color             Disable ANSI colors (also via NO_COLOR env var)
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

# Respect NO_COLOR (https://no-color.org) and non-tty output (CI logs)
if [ -n "${NO_COLOR:-}" ] || [ ! -t 1 ]; then
  RED=''; GREEN=''; YELLOW=''; CYAN=''; NC=''
fi

log()  { printf "${CYAN}[deploy]${NC} %s\n" "$*"; }
ok()   { printf "${GREEN}[deploy]${NC} ✅ %s\n" "$*"; }
warn() { printf "${YELLOW}[deploy]${NC} ⚠️  %s\n" "$*"; }
err()  { printf "${RED}[deploy]${NC} ❌ %s\n" "$*" >&2; exit 1; }

STACK_NAME=${STACK_NAME:-cryptoprice}
DO_BUILD=true
REGISTRY_ONLY=false
REGISTRY_PORT=5000
MANAGER_IP=""

# ── Parse arguments ──────────────────────────────────────────────────────────
for arg in "$@"; do
  case "$arg" in
    --skip-build)        DO_BUILD=false ;;
    --build)             DO_BUILD=true ;;
    --registry-only)     REGISTRY_ONLY=true; DO_BUILD=true ;;
    --registry-port=*)   REGISTRY_PORT="${arg#*=}" ;;
    --no-color)          RED=''; GREEN=''; YELLOW=''; CYAN=''; NC='' ;;
    -h|--help)
      sed -n '2,20p' "$0"
      exit 0
      ;;
    *)                   warn "Unknown argument: $arg" ;;
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

# Get the manager node's IP for the registry
MANAGER_IP=$(docker info --format '{{.Swarm.NodeAddr}}' 2>/dev/null || true)
if [ -z "$MANAGER_IP" ]; then
  MANAGER_IP="127.0.0.1"
  warn "Could not detect Swarm advertise address; using 127.0.0.1 for registry."
fi
REGISTRY_ADDR="${MANAGER_IP}:${REGISTRY_PORT}"

# Verify node labels
CORE_NODES=$(docker node ls -q 2>/dev/null | xargs -r docker node inspect --format '{{ index .Spec.Labels "role" }}' 2>/dev/null | grep -c '^core$' || true)
WORKER_NODES=$(docker node ls -q 2>/dev/null | xargs -r docker node inspect --format '{{ index .Spec.Labels "role" }}' 2>/dev/null | grep -c '^worker$' || true)

if [ "$CORE_NODES" -eq 0 ]; then
  warn "No nodes with label role=core found. Run: docker node update --label-add role=core <node-id>"
fi
if [ "$WORKER_NODES" -eq 0 ]; then
  warn "No nodes with label role=worker found. Run: docker node update --label-add role=worker <node-id>"
fi

ok "Preflight checks passed (core=$CORE_NODES, worker=$WORKER_NODES nodes)"

# ── Ensure local registry is running ─────────────────────────────────────────
log "Ensuring local Docker registry at ${REGISTRY_ADDR}..."

if ! docker service ls --filter "name=registry" --format '{{.Name}}' 2>/dev/null | grep -q '^registry$'; then
  log "Creating Swarm registry service..."
  docker service create \
    --name registry \
    --publish published=${REGISTRY_PORT},target=5000 \
    --constraint 'node.role == manager' \
    --mount type=volume,source=registry-data,target=/var/lib/registry \
    registry:2 >/dev/null 2>&1
  ok "Registry service created."

  # Wait for registry to be ready
  log "Waiting for registry to start..."
  for i in $(seq 1 30); do
    if curl -sf "http://${REGISTRY_ADDR}/v2/" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
  if ! curl -sf "http://${REGISTRY_ADDR}/v2/" >/dev/null 2>&1; then
    err "Registry failed to start within 30 seconds."
  fi
  ok "Registry is ready."
else
  # Ensure existing registry is healthy
  if ! curl -sf "http://${REGISTRY_ADDR}/v2/" >/dev/null 2>&1; then
    warn "Registry service exists but is not responding. Waiting..."
    for i in $(seq 1 15); do
      if curl -sf "http://${REGISTRY_ADDR}/v2/" >/dev/null 2>&1; then
        break
      fi
      sleep 2
    done
  fi
  ok "Registry already running at ${REGISTRY_ADDR}."
fi

# ── Build images locally ────────────────────────────────────────────────────
if [ "$DO_BUILD" = true ]; then
  log "Building images locally (prod profile)..."
  docker compose --profile prod --profile monitoring --profile logging build
  ok "Images built successfully."
else
  log "Skipping image build (--skip-build)."
fi

# ── Push custom images to the local registry ─────────────────────────────────
# Only custom-built images need to be pushed; public images (redis, postgres,
# etc.) are pulled directly by each node from Docker Hub.
CUSTOM_IMAGES=(
  "cryptoprice/flink:1.18.1"
  "cryptoprice/spark:3.5.5"
  "cryptoprice/spark-submit:local"
  "cryptoprice/fastapi:0.25.0"
  "cryptoprice/nginx:1.31.0"
  "cryptoprice/producer:0.25.0"
  "cryptoprice/binance-ticker-ws:0.1.0"
  "cryptoprice/binance-kline-rest:0.1.0"
  "cryptoprice/influx-backfill:0.25.0"
  "cryptoprice/trino:442"
  "cryptoprice/dagster:1.8.10"
  "cryptoprice/ai-service:latest"
)

log "Pushing ${#CUSTOM_IMAGES[@]} custom images to local registry (${REGISTRY_ADDR})..."
for img in "${CUSTOM_IMAGES[@]}"; do
  if docker image inspect "$img" >/dev/null 2>&1; then
    registry_tag="${REGISTRY_ADDR}/${img}"
    docker tag "$img" "$registry_tag"
    docker push "$registry_tag" >/dev/null 2>&1
    printf "  ✅ %s\n" "$img"
  else
    printf "  ⚠️  %s (not found locally, skipping)\n" "$img"
  fi
done
ok "Custom images pushed to registry."

if [ "$REGISTRY_ONLY" = true ]; then
  ok "Registry push complete (--registry-only). Exiting."
  exit 0
fi

# ── Deploy the stack ─────────────────────────────────────────────────────────
RENDERED_STACK_FILE="$(mktemp /tmp/lmview-stack-XXXXXX.yml)"
BACKUP_STACK_FILE="/tmp/lmview-stack-backup-${STACK_NAME}.yml"

cleanup() {
  rm -f "$RENDERED_STACK_FILE"
}
trap cleanup EXIT

# IB-3: Snapshot current stack before deploy for rollback
SNAPSHOT_EXISTS=false
if docker stack services "$STACK_NAME" >/dev/null 2>&1; then
  SNAPSHOT_EXISTS=true
  log "Snapshotting current stack state to ${BACKUP_STACK_FILE}..."
  CURRENT_STACK="$(docker compose --profile prod --profile monitoring --profile logging --profile ai-api \
    -f docker-compose.yml \
    -f docker-compose.ai.yml \
    -f docker-compose.swarm.yml \
    config 2>/dev/null || true)"
  if [ -n "$CURRENT_STACK" ]; then
    echo "$CURRENT_STACK" > "$BACKUP_STACK_FILE"
    ok "Stack state snapshotted (${#CURRENT_STACK} bytes)"
  else
    warn "Could not snapshot current stack state; rollback unavailable"
    SNAPSHOT_EXISTS=false
  fi
fi

log "Rendering expanded Compose config for Swarm..."
docker compose --profile prod --profile monitoring --profile logging --profile ai-api \
  -f docker-compose.yml \
  -f docker-compose.ai.yml \
  -f docker-compose.swarm.yml \
  config > "$RENDERED_STACK_FILE"

# Port normalization: remove quotes from published/target port numbers
# Moved from sed to the Python YAML step below (IB-2 fix)

python3 - "$RENDERED_STACK_FILE" "$REGISTRY_ADDR" <<'PY'
import sys
from pathlib import Path
from collections.abc import MutableMapping

import yaml

path = Path(sys.argv[1])
registry_addr = sys.argv[2]
data = yaml.safe_load(path.read_text())

if isinstance(data, MutableMapping):
  data.pop('name', None)

  services = data.get('services')
  if isinstance(services, MutableMapping):
    for service_config in services.values():
      if not isinstance(service_config, MutableMapping):
        continue

      service_config.pop('profiles', None)
      service_config.pop('container_name', None)
      service_config.pop('depends_on', None)
      service_config.pop('build', None)
      service_config.pop('restart', None)

      # Rewrite custom image tags to point at the local registry
      image = service_config.get('image', '')
      if image.startswith('cryptoprice/'):
        service_config['image'] = f'{registry_addr}/{image}'

      # IB-2: Normalize port definitions (remove string quoting on numeric ports)
      ports = service_config.get('ports', [])
      if isinstance(ports, list):
        normalized_ports = []
        for port in ports:
          if isinstance(port, dict):
            for key in ('published', 'target'):
              val = port.get(key)
              if isinstance(val, str) and val.isdigit():
                port[key] = int(val)
          normalized_ports.append(port)
        service_config['ports'] = normalized_ports

path.write_text(yaml.safe_dump(data, sort_keys=False))
PY

log "Deploying stack '$STACK_NAME'..."
if docker stack deploy \
  --resolve-image never \
  -c "$RENDERED_STACK_FILE" \
  "$STACK_NAME"; then
  ok "Stack '$STACK_NAME' deployed."
  # Deploy succeeded — save rendered config as new backup
  cp "$RENDERED_STACK_FILE" "$BACKUP_STACK_FILE"
  log "Updated rollback snapshot"
else
  err "Stack deploy FAILED."
  # IB-3: Attempt rollback from previous snapshot
  if [ "$SNAPSHOT_EXISTS" = true ] && [ -f "$BACKUP_STACK_FILE" ]; then
    warn "Rolling back to previous stack state..."
    if docker stack deploy --resolve-image never -c "$BACKUP_STACK_FILE" "$STACK_NAME"; then
      ok "Rollback complete — stack restored to pre-deploy state."
    else
      err "Rollback also failed. Manual intervention required."
    fi
  else
    warn "No rollback snapshot available. Manual intervention required."
  fi
  exit 1
fi

# ── Post-deployment status ───────────────────────────────────────────────────
log "Waiting 10s for services to start..."
sleep 10

echo ""
log "Service status:"
docker stack services "$STACK_NAME"

echo ""
log "Running tasks:"
docker stack ps "$STACK_NAME" --filter "desired-state=running" --format "table {{.Name}}\t{{.Node}}\t{{.CurrentState}}" | head -50

echo ""
ok "Deployment complete!"
echo ""
log "Next steps:"
echo "  1. Verify all services:       docker stack services $STACK_NAME"
echo "  2. Check service logs:        docker service logs ${STACK_NAME}_fastapi-prod"
echo "  3. Monitor node status:       docker node ls"
echo "  4. Access the app at:         https://\${CERTBOT_DOMAIN}"
echo ""
log "Management commands:"
echo "  make swarm-status             Show service & task status"
echo "  make swarm-deploy-quick       Deploy without rebuilding images"
echo "  make swarm-logs SVC=fastapi   Tail logs for a service"
echo "  make swarm-down               Remove the stack"
echo ""
warn "Ensure AWS Security Groups allow:"
echo "  - TCP 2377  (Swarm management)     — between nodes"
echo "  - TCP 7946  (Swarm gossip)         — between nodes"
echo "  - UDP 7946  (Swarm gossip)         — between nodes"
echo "  - UDP 4789  (VXLAN overlay)        — between nodes"
echo "  - TCP 80    (HTTP)                 — public"
echo "  - TCP 443   (HTTPS)                — public"
echo "  - TCP 5000  (Registry)             — between nodes"
echo "  - TCP 8080  (FastAPI, optional)    — internal/admin"
