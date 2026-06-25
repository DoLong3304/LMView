#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# sync_worker_images.sh — Mirror missing Swarm images from manager to worker
# ─────────────────────────────────────────────────────────────────────────────
# Swarm workers that cannot pull from the manager-local registry (firewall
# blocking port 5000) get "No such image" and tasks stay Shutdown-Rejected.
# This script syncs images via save→scp→load→tag.
#
# Usage:
#   WORKER_HOST=ubuntu@10.0.0.2 REGISTRY_HOST=10.0.0.1:5000 \
#     bash scripts/sync_worker_images.sh [--dry-run]
#
# Required env vars:
#   WORKER_HOST   SSH target for the worker node (e.g., ubuntu@10.0.0.2)
#   REGISTRY_HOST Registry address resolvable on worker (e.g., 10.0.0.1:5000)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# ── Required config ─────────────────────────────────────────────────────────
WORKER_HOST="${WORKER_HOST:-}"
REGISTRY_HOST="${REGISTRY_HOST:-localhost:5000}"

if [ -z "$WORKER_HOST" ]; then
  echo "ERROR: WORKER_HOST must be set (e.g., ubuntu@10.0.0.2)"
  echo "Usage: WORKER_HOST=ubuntu@10.0.0.2 REGISTRY_HOST=10.0.0.1:5000 $0"
  exit 1
fi

# ── Args ────────────────────────────────────────────────────────────────────
DRY_RUN=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)        DRY_RUN=true; shift ;;
    -h|--help)
      sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

# ── Color helpers ────────────────────────────────────────────────────────────
RED=$'\033[0;31m'; GREEN=$'\033[0;32m'; YELLOW=$'\033[1;33m'
CYAN=$'\033[0;36m'; NC=$'\033[0m'
log()  { printf "${CYAN}[sync]${NC} %s\n" "$*"; }
ok()   { printf "${GREEN}[sync]${NC} ✅ %s\n" "$*"; }
warn() { printf "${YELLOW}[sync]${NC} ⚠️  %s\n" "$*"; }
err()  { printf "${RED}[sync]${NC} ❌ %s\n" "$*" >&2; exit 1; }

run() {
  if $DRY_RUN; then
    printf "${YELLOW}[dry-run]${NC} %s\n" "$*"
  else
    eval "$@"
  fi
}

# ── Image list ──────────────────────────────────────────────────────────────
# Resolve from docker compose config so it stays in sync automatically.
log "Resolving custom image tags from compose config..."
IMAGES=()
while IFS= read -r img; do
  if [ -n "$img" ]; then
    IMAGES+=("$img")
  fi
done < <(docker compose --profile prod config 2>/dev/null | grep 'image: cryptoprice/' | awk '{print $2}' | sort -u)

if [ ${#IMAGES[@]} -eq 0 ]; then
  err "No custom images found. Run from project root with docker-compose.yml."
fi
log "Found ${#IMAGES[@]} custom images."

# ── Step 1: Probe reachability ──────────────────────────────────────────────
log "Probing ${WORKER_HOST} -> ${REGISTRY_HOST} reachability..."
if $DRY_RUN; then
  warn "DRY-RUN: skipping ssh probe"
else
  FIRST_IMAGE="${IMAGES[0]}"
  if ssh -o BatchMode=yes -o ConnectTimeout=5 "$WORKER_HOST" \
        "docker pull ${REGISTRY_HOST}/${FIRST_IMAGE}" >/tmp/sync_probe.log 2>&1; then
    ok "Worker can pull directly from registry — manual recovery NOT needed."
    exit 0
  fi
  warn "Direct pull failed (see /tmp/sync_probe.log). Falling back to save/scp/load."
fi

# ── Step 2: docker save -> scp -> docker load -> tag ──────────────────────────
STAGE_DIR="/tmp/lmview-sync-$(date +%s)"
mkdir -p "$STAGE_DIR"

for img in "${IMAGES[@]}"; do
  archive="${STAGE_DIR}/$(echo "$img" | tr '/:' '__').tgz"
  log "Saving ${img} -> ${archive}"
  run "docker save '${img}' -o '${archive}'"

  log "Copying ${archive##*/} -> ${WORKER_HOST}:${archive}"
  run "scp '${archive}' '${WORKER_HOST}:${archive}'"

  log "Loading on ${WORKER_HOST}"
  run "ssh '${WORKER_HOST}' \"docker load -i '${archive}'\""

  remote_full="${REGISTRY_HOST}/${img}"
  log "Tagging ${img} -> ${remote_full} on worker"
  run "ssh '${WORKER_HOST}' \"docker tag '${img}' '${remote_full}'\""
done

# ── Step 4: Verify ───────────────────────────────────────────────────────────
log "Verifying images on worker..."
verify_cmd="docker images --format '{{.Repository}}:{{.Tag}}' | sort"
run "ssh '${WORKER_HOST}' \"${verify_cmd}\""

# ── Step 5: Cleanup ──────────────────────────────────────────────────────────
log "Cleaning up local stage dir ${STAGE_DIR}"
run "rm -rf '${STAGE_DIR}'"
run "ssh '${WORKER_HOST}' 'rm -rf ${STAGE_DIR}'"

ok "Worker image sync complete. Next: bash scripts/restart_swarm_services.sh"
