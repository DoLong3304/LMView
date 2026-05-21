#!/bin/bash
set -e

# JMX Prometheus Agent for Trino
# Jar is pre-staged at build time in /opt/trino-jmx/.
# Config yaml is mounted from host at /etc/trino/jmx/ (read-only).
JMX_JAR="/opt/trino-jmx/jmx_prometheus_javaagent.jar"
JMX_CFG="/etc/trino/jmx/trino-442.yaml"

# Substituting env-var placeholders in Trino catalog properties
CATALOG="/etc/trino/catalog/iceberg.properties"
if [ -f "$CATALOG" ]; then
  sed -i \
    -e "s|__POSTGRES_USER__|${POSTGRES_USER:?POSTGRES_USER is required}|g" \
    -e "s|__POSTGRES_PASSWORD__|${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}|g" \
    -e "s|__MINIO_ROOT_USER__|${MINIO_ROOT_USER:?MINIO_ROOT_USER is required}|g" \
    -e "s|__MINIO_ROOT_PASSWORD__|${MINIO_ROOT_PASSWORD:?MINIO_ROOT_PASSWORD is required}|g" \
    "$CATALOG"
fi

# Append JMX agent to jvm.config (Trino reads JVM opts from this file, not CLI args)
JVM_CONFIG="/etc/trino/jvm.config"
if [ -f "$JMX_JAR" ] && [ -f "$JMX_CFG" ]; then
  JMX_PORT="${JMX_EXPORTER_PORT:-9404}"
  echo "-javaagent:${JMX_JAR}=${JMX_PORT}:${JMX_CFG}" >> "$JVM_CONFIG"
  echo "JMX Prometheus agent enabled on port ${JMX_PORT}"
fi

exec /usr/lib/trino/bin/run-trino "$@"
