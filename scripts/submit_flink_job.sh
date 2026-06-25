#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# submit_flink_job.sh — Submit the Flink pipeline via REST API
# ─────────────────────────────────────────────────────────────────────────────
# Can be run from either manager or worker node (Flink REST API is publicly
# reachable on port 8081). Uploads pipeline.py + deps.zip as a single job.
#
# Usage:
#   bash scripts/submit_flink_job.sh [--wait-slots]
#
# Options:
#   --wait-slots  Block until at least 1 slot is available (timeout 5 min)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

WAIT_SLOTS=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --wait-slots) WAIT_SLOTS=true; shift ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

FLINK_JM_URL="${FLINK_JM_URL:-http://localhost:8081}"
FLINK_PARALLELISM="${FLINK_PARALLELISM:-12}"
REGISTRY_ADDR="${REGISTRY_ADDR:-localhost:5000}"
FLINK_IMAGE="${FLINK_IMAGE:-${REGISTRY_ADDR}/cryptoprice/flink:1.18.1}"

RED=$'\033[0;31m'; GREEN=$'\033[0;32m'; YELLOW=$'\033[1;33m'
CYAN=$'\033[0;36m'; NC=$'\033[0m'
log()  { printf "${CYAN}[submit]${NC} %s\n" "$*"; }
ok()   { printf "${GREEN}[submit]${NC} ✅ %s\n" "$*"; }
warn() { printf "${YELLOW}[submit]${NC} ⚠️  %s\n" "$*"; }
err()  { printf "${RED}[submit]${NC} ❌ %s\n" "$*" >&2; exit 1; }

# 1. Wait for slots if requested
if $WAIT_SLOTS; then
  log "Waiting for Flink slots (timeout 300s)..."
  for i in $(seq 1 60); do
    slots=$(curl -sf "${FLINK_JM_URL}/overview" 2>/dev/null | grep -oP '"slots-available":\K\d+' || echo 0)
    if [[ "$slots" -gt 0 ]]; then
      ok "Slots available: $slots"
      break
    fi
    printf "."
    sleep 5
  done
  if [[ "$slots" == "0" ]]; then
    err "No slots after 300s. Apply IB-10 workaround first."
  fi
fi

# 2. Build deps.zip on a flink image that has the same Python env
log "Building deps.zip from flink image..."
docker run --rm \
  --network host \
  -v "$PROJECT_ROOT/src:/app/src:ro" \
  -v "$PROJECT_ROOT/schemas:/app/schemas:ro" \
  ${FLINK_IMAGE} \
  bash /app/scripts/build_deps_zip.sh 2>&1 | tail -3

# 3. Submit job via REST API
log "Submitting pipeline.py via Flink REST API..."
RESP=$(docker run --rm \
  --network host \
  -v "$PROJECT_ROOT/src:/app/src:ro" \
  -v "$PROJECT_ROOT/schemas:/app/schemas:ro" \
  ${FLINK_IMAGE} \
  bash -c "
    cd /tmp && flink run \
      -m ${FLINK_JM_URL#http://} \
      -d \
      -py /app/src/processing/pipeline.py \
      --pyFiles /tmp/deps.zip
  " 2>&1)
echo "$RESP" | tail -10

ok "Job submitted. Check: curl -s $FLINK_JM_URL/jobs"
