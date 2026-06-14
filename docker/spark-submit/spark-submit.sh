#!/bin/bash
# Spark streaming supervisor.
#
# Submits the Kafka -> Iceberg pipeline to spark-master and restarts it
# if the SparkSubmit JVM exits (OOM, code error, etc.). Logs go to
# stdout for Promtail/Loki; no local file persistence.
#
# Env:
#   SPARK_MASTER_URL  - default spark://spark-master:7077
#   PIPELINE_PATH     - default /app/src/lakehouse/pipeline.py
#   RESTART_DELAY     - default 15 seconds between restarts
#
# The script keeps a monotonically increasing run counter in the log
# line so on-call engineers can tell whether they're looking at
# restart #1 or restart #47 of the same container.

set -u

SPARK_MASTER_URL="${SPARK_MASTER_URL:-spark://spark-master:7077}"
PIPELINE_PATH="${PIPELINE_PATH:-/app/src/lakehouse/pipeline.py}"
RESTART_DELAY="${RESTART_DELAY:-15}"

# Wait for spark-master to be reachable before we start anything.
echo "[supervisor] waiting for spark-master at ${SPARK_MASTER_URL} ..."
for i in $(seq 1 60); do
    if curl -fsS --max-time 2 "http://spark-master:8080/json/" >/dev/null 2>&1; then
        echo "[supervisor] spark-master is up after ${i} attempts"
        break
    fi
    sleep 2
done

SPARK_PACKAGES='org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.2,org.apache.iceberg:iceberg-aws-bundle:1.5.2,org.apache.hadoop:hadoop-aws:3.3.4,org.postgresql:postgresql:42.7.2,org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.5,org.apache.spark:spark-avro_2.12:3.5.5'

run=0
while true; do
    run=$((run + 1))
    echo "[supervisor] run #${run}: spark-submit ${PIPELINE_PATH}"
    /opt/spark/bin/spark-submit \
        --master "${SPARK_MASTER_URL}" \
        --total-executor-cores 2 \
        --packages "${SPARK_PACKAGES}" \
        --conf spark.driver.memory=1g \
        --conf spark.executor.memory=1g \
        "${PIPELINE_PATH}" \
    2>&1 | sed "s/^/[run ${run}] /"

    rc="${PIPESTATUS[0]}"
    echo "[supervisor] spark-submit exited rc=${rc}; sleeping ${RESTART_DELAY}s before restart"
    sleep "${RESTART_DELAY}"
done
