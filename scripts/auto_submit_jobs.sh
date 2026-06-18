#!/bin/bash
set -e

FLINK_HEALTH_URL="${FLINK_HEALTH_URL:-http://flink-jobmanager:8081}"
FLINK_HOST="${FLINK_HEALTH_URL#http://}"
FLINK_HOST="${FLINK_HOST#https://}"
SPARK_HEALTH_URL="${SPARK_HEALTH_URL:-http://spark-master:8080}"

# ==========================================
# 0. Pre-flight: verify Schema Registry reachable
# ==========================================
SCHEMA_REGISTRY_URL="${SCHEMA_REGISTRY_URL:-http://schema-registry:8080/apis/ccompat/v7}"
MAX_RETRIES=12
RETRY_INTERVAL=10

echo "Waiting for Schema Registry at $SCHEMA_REGISTRY_URL ..."
for i in $(seq 1 $MAX_RETRIES); do
  if curl -sf --connect-timeout 5 --max-time 10 "$SCHEMA_REGISTRY_URL/subjects" > /dev/null 2>&1; then
    echo " Schema Registry ready after ${i} attempts."
    break
  fi
  if [ $i -eq $MAX_RETRIES ]; then
    echo "WARNING: Schema Registry not reachable after $MAX_RETRIES attempts — proceeding anyway (SR might be up soon)"
  fi
  echo "  attempt $i/$MAX_RETRIES ..."
  sleep $RETRY_INTERVAL
done

# ==========================================
# 1. WAIT FOR FLINK
# ==========================================
echo "Waiting for Flink JobManager at $FLINK_HEALTH_URL ..."
until curl -sf --connect-timeout 5 "$FLINK_HEALTH_URL/overview" > /dev/null 2>&1; do
    printf '.'
    sleep 5
done
echo " Flink JobManager ready!"

# Wait for TaskManagers to register
echo "Waiting for TaskManagers to register (30s) ..."
sleep 30

# ==========================================
# 2. CANCEL OLD FAILED JOBS
# ==========================================
FAILED_JOBS=$(curl -sf "$FLINK_HEALTH_URL/jobs" 2>/dev/null | \
  python3 -c "import sys,json; [print(j['id']) for j in json.load(sys.stdin)['jobs'] if j['status'] in ('FAILED','CANCELED','RESTARTING')]" 2>/dev/null || true)
if [ -n "$FAILED_JOBS" ]; then
  echo "Canceling old failed jobs: $FAILED_JOBS"
  for JOB_ID in $FAILED_JOBS; do
    curl -sf -X PATCH "$FLINK_HEALTH_URL/jobs/$JOB_ID?mode=cancel" > /dev/null 2>&1 || true
    echo "  canceled $JOB_ID"
  done
  sleep 5
fi

# ==========================================
# 3. BUILD deps.zip  (done via REST API — no docker.sock needed)
# ==========================================
DEPS_DIR="/tmp/flink_deps"
mkdir -p "$DEPS_DIR"
SRC_DIR="/app/src"

# Write Python deps zip via stdin to avoid large shell quoting issues
python3 - <<'PYEOF'
import zipfile, os, sys

src = os.environ.get("SRC_DIR", "/app/src")
out = "/tmp/flink_deps/deps.zip"

STDLIB_SHADOW = {'logging.py'}

zf = zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED)

# common package
for root, dirs, files in os.walk(os.path.join(src, 'common')):
    for f in files:
        if f.endswith('.py') and f not in STDLIB_SHADOW:
            fp = os.path.join(root, f)
            zf.write(fp, os.path.relpath(fp, src))

# writers package (flattened)
zf.writestr('writers/__init__.py', '')
writers_dir = os.path.join(src, 'processing', 'writers')
for root, dirs, files in os.walk(writers_dir):
    for f in files:
        if f.endswith('.py') and f != '__init__.py':
            fp = os.path.join(root, f)
            zf.write(fp, 'writers/' + f)

zf.close()
print(f"deps.zip created: {out} ({os.path.getsize(out)} bytes)")
PYEOF

# ==========================================
# 4. SUBMIT FLINK JOB via REST API
# ==========================================
echo "=== Submitting Flink job via REST ==="
curl -sf -X POST "$FLINK_HEALTH_URL/jobs" \
  -H "Content-Type: application/json" \
  -d "{
    \"programArg\": \"\",
    \"entryPoint\": \"python\",
    \"properties\": {
      \" parallelism\": 1,
      \"pyFiles\": [\"/tmp/flink_deps/deps.zip\"],
      \"programOptions\": \"-py /app/src/processing/pipeline.py\"
    }
  }" 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "Note: REST submit might not support pyFiles — falling back to flink CLI via HTTP"

# Best approach: use flink CLI pointing to REST endpoint
# The flink CLI with -m <jobmanager-host:port> submits via HTTP REST
# Container has 'flink' binary available
echo "Submitting via flink CLI -m (REST) ..."

# Create a small script to run inside the flink-jobmanager container
# but we can't use docker exec in Swarm. Use flink CLI from auto-submit container instead.
# auto-submit container has flink CLI already.
# We call the same flink run -m approach as the one-shot auto-submit-jobs service.

# Check if we can curl the jar endpoint
JARS=$(curl -sf "$FLINK_HEALTH_URL/jars" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print([f['id'] for f in d.get('files',[])])" 2>/dev/null || echo "[]")
echo "Uploaded jars: $JARS"

# Since we don't have a pre-built jar and Python submit via REST is tricky,
# let's use the flink CLI with -m flag from THIS container (which has flink CLI)
/opt/flink/bin/flink run -d \
  -m "$FLINK_HOST" \
  -py /app/src/processing/pipeline.py \
  --pyFiles /tmp/flink_deps/deps.zip \
  2>&1 || echo "Flink CLI failed, trying alternative..."

# ==========================================
# 5. SPARK (if available)
# ==========================================
echo "Waiting for Spark Master at $SPARK_HEALTH_URL ..."
until curl -sf --connect-timeout 5 "$SPARK_HEALTH_URL/json/" > /dev/null 2>&1; do
    printf '.'
    sleep 5
done
echo " Spark Master ready!"

# Spark submit via spark:// URL (not docker exec)
if command -v spark-submit &>/dev/null; then
  echo "Submitting Spark job ..."
  spark-submit \
    --master spark://spark-master:7077 \
    --total-executor-cores 2 \
    --repositories https://repo1.maven.org/maven2 \
    --packages "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.2,org.apache.iceberg:iceberg-aws-bundle:1.5.2,org.apache.hadoop:hadoop-aws:3.3.4,org.postgresql:postgresql:42.7.2,org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.5,org.apache.spark:spark-avro_2.12:3.5.5" \
    --conf spark.driver.memory=1g \
    --conf spark.executor.memory=1g \
    /app/src/lakehouse/pipeline.py \
    2>&1 || echo "Spark submit failed (non-fatal)"
else
  echo "spark-submit not available — skipping Spark job"
fi

echo "=== auto_submit_jobs.sh complete ==="