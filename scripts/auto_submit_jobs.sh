#!/bin/bash

FLINK_HEALTH_URL="${FLINK_HEALTH_URL:-http://127.0.0.1:8081}"
# IB-4 fix: spark-master DNS works inside Swarm overlay network
# Script must run in a container attached to the same overlay network.
SPARK_HEALTH_URL="${SPARK_HEALTH_URL:-http://spark-master:8080}"

# ==========================================
# 1. START FLINK
# ==========================================
echo "Waiting for Flink Cluster to be ready on port 8081..."
# curl -s hides output; loop exits once the endpoint is reachable
until curl -s "$FLINK_HEALTH_URL" > /dev/null; do
    printf '.'
    sleep 5
done
echo " Flink is ready!"

# Wait for TaskManagers to register with JobManager
echo "Waiting for TaskManagers to register..."
MAX_WAIT=120
INTERVAL=5
elapsed=0
while [ $elapsed -lt $MAX_WAIT ]; do
  slots=$(curl -sf "${FLINK_HEALTH_URL}/overview" 2>/dev/null | grep -oP '"slots-available":\K\d+' || echo 0)
  if [ "$slots" -gt 0 ]; then
    echo "TaskManagers ready (${slots} slots available)"
    break
  fi
  echo "  waiting for slots... (${elapsed}s elapsed)"
  sleep $INTERVAL
  elapsed=$((elapsed + INTERVAL))
done

if [ "$slots" -eq 0 ]; then
  echo "ERROR: No TaskManager slots available after ${MAX_WAIT}s"
  exit 1
fi

# Submit Flink job in detached mode (-d)
# Build shared deps.zip (DP-2: extracted to shared script)
bash /app/scripts/build_deps_zip.sh 2>&1 || bash scripts/build_deps_zip.sh 2>&1

# Submit with the zip file (jobmanager accessible via service DNS)
cd /app/src && flink run -d -m flink-jobmanager:8081 -py processing/pipeline.py --pyFiles /tmp/deps.zip
echo "Submitted Flink job."


# ==========================================
# 2. START SPARK
# ==========================================
echo "Waiting for Spark Master to be ready on port 8080..."
# curl -s checks Spark master endpoint availability
until curl -s "$SPARK_HEALTH_URL" > /dev/null; do
    printf '.'
    sleep 5
done
echo " Spark Master is ready!"

# Submit Spark job in detached mode (skip for now - spark-submit not available in auto-submit container)
echo "spark-submit not available in auto-submit-jobs container — skipping Spark job"
echo "(Run Spark job separately via spark-submit container or manual submission)"

echo "=== auto_submit_jobs.sh complete ==="