#!/usr/bin/env bash
# docker-reclaim.sh — One-shot disk reclamation for cryptoprice stack.
# Reclaimable today: ~75 GB (Spark work dirs 48GB + dangling image 8.6GB + prune 9GB + builder 13.8GB)
set -euo pipefail

LOG() { printf "\033[1;36m[reclaim]\033[0m %s\n" "$*"; }
WARN() { printf "\033[1;33m[reclaim]\033[0m %s\n" "$*"; }
DIE() { printf "\033[1;31m[reclaim]\033[0m %s\n" "$*" >&2; exit 1; }

[[ "$(uname -r)" == *microsoft* ]] || DIE "Must run inside WSL (this script targets WSL2 docker-desktop)."

LOG "=== Pre-state ==="
docker system df

# ─── 1. Spark worker work-dir purge (the 48 GB monster) ────────────────────
LOG "Purging /opt/spark/work on both workers (saves ~48 GB)..."
for c in spark-worker spark-worker-2; do
  if docker ps -a --format '{{.Names}}' | grep -qx "$c"; then
    if docker exec "$c" test -d /opt/spark/work 2>/dev/null; then
      size=$(docker exec "$c" du -sb /opt/spark/work 2>/dev/null | awk '{print $1}')
      LOG "  $c work dir = $(numfmt --to=iec --suffix=B "$size" 2>/dev/null || echo "${size}B")"
      docker exec "$c" sh -c 'rm -rf /opt/spark/work/app-* && echo "purged"'
    fi
  else
    WARN "  $c not running, skipping"
  fi
done

# ─── 2. Dangling / unused images (~18 GB) ─────────────────────────────────
LOG "Pruning dangling images..."
docker image prune -f

LOG "Pruning unused images (only those not used by any container)..."
docker image prune -af --filter "until=72h" 2>/dev/null || docker image prune -af

# ─── 3. Build cache (13.8 GB) ─────────────────────────────────────────────
LOG "Pruning buildx cache..."
docker builder prune -af --filter "until=72h" 2>/dev/null || docker builder prune -af

# ─── 4. Dangling volumes (saves a few hundred MB) ─────────────────────────
LOG "Pruning dangling volumes..."
docker volume prune -f

# ─── 5. Container filesystem diffs (overlay whiteout) ─────────────────────
LOG "Pruning stopped containers' writable layers..."
docker container prune -f

LOG "=== Post-state ==="
docker system df

LOG "Next: run docker-compact-vhdx.ps1 from PowerShell (admin) to shrink the VHDX file itself."
