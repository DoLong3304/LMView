#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# submit_flink.sh — Build deps.zip and submit Flink streaming pipeline
# ─────────────────────────────────────────────────────────────────────────────
# Uses the shared build_deps_zip.sh for the package step.
# Must run inside a container with /app/src on the same overlay network as
# flink-jobmanager.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

echo "[submit_flink] Building deps.zip..."
bash /app/scripts/build_deps_zip.sh 2>&1 || bash scripts/build_deps_zip.sh 2>&1
echo "[submit_flink] deps.zip ready. Submitting pipeline..."

cd /app/src && flink run -d -m flink-jobmanager:8081 -py processing/pipeline.py --pyFiles /tmp/deps.zip
echo "[submit_flink] Job submitted."
