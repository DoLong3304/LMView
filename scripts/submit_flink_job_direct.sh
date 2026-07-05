#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# submit_flink_job_direct.sh — Submit Flink pipeline directly (no docker)
# ─────────────────────────────────────────────────────────────────────────────
# Designed to run inside the Flink container (or any container with flink CLI).
# Builds deps.zip and submits via flink run.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

FLINK_JM_URL="${FLINK_JM_URL:-flink-jobmanager:8081}"
# Remove protocol prefix if present (flink -m expects host:port only)
FLINK_JM_URL="${FLINK_JM_URL#http://}"
FLINK_JM_URL="${FLINK_JM_URL#https://}"
SRC_DIR="${SRC_DIR:-/app/src}"
FLINK_PARALLELISM="${FLINK_PARALLELISM:-12}"

# config.sh mistakenly derives FLINK_HOME from \$0 path when sourced from
# a different script.  Fix it explicitly so flink run -py finds flink-python.
FLINK_HOME=/opt/flink
FLINK_LIB_DIR=$FLINK_HOME/lib

echo "[submit] Building deps.zip..."
bash /app/scripts/build_deps_zip.sh

echo "[submit] Submitting pipeline.py to Flink at ${FLINK_JM_URL}..."

# PYTHONPATH replaces --pyFiles /tmp/deps.zip because the source code is
# accessible to all nodes via the shared EFS mount at /app/src.
export PYTHONPATH="/app/src/processing:/app/src:${PYTHONPATH:-}"

flink run \
  -m "${FLINK_JM_URL}" \
  -d \
  -py "${SRC_DIR}/processing/pipeline.py" \
  2>&1

echo "[submit] ✅ Done. Check: curl -s http://${FLINK_JM_URL}/jobs"
