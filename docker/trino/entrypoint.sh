#!/bin/bash
set -e

# JMX Prometheus Agent for Trino
JMX_JAR="/etc/trino/jmx/jmx_prometheus_javaagent.jar"
JMX_CFG="/etc/trino/jmx/trino-442.yaml"
if [ -f "$JMX_CFG" ] && [ ! -f "$JMX_JAR" ]; then
  echo "Downloading jmx_prometheus_javaagent..."
  mkdir -p /etc/trino/jmx
  wget -q -O "$JMX_JAR" \
    "https://repo1.maven.org/maven2/io/prometheus/jmx/jmx_prometheus_javaagent/0.20.0/jmx_prometheus_javaagent-0.20.0.jar"
fi

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

# Build Trino JVM opts (prepend JMX agent if config exists)
TRINO_OPTS=""
if [ -f "$JMX_JAR" ] && [ -f "$JMX_CFG" ]; then
  JMX_PORT="${JMX_EXPORTER_PORT:-9404}"
  TRINO_OPTS="-javaagent:${JMX_JAR}=${JMX_PORT}:${JMX_CFG}"
  echo "JMX Prometheus agent enabled on port ${JMX_PORT}"
fi

ALL_OPTS="${TRINO_OPTS} ${JVM_EXTRA_OPTS:-}"

exec /usr/lib/trino/bin/run-trino "$@" $ALL_OPTS
