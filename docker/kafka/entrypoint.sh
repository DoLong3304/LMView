#!/bin/bash
set -e

# ─── JMX Prometheus Agent Setup ─────────────────────────────────────────────────
JMX_DIR="/tmp/jmx"
JMX_JAR="$JMX_DIR/jmx_prometheus_javaagent.jar"
mkdir -p "$JMX_DIR"

if [ ! -f "$JMX_JAR" ]; then
  echo "Downloading jmx_prometheus_javaagent..."
  wget -q -O "$JMX_JAR" \
    "https://repo1.maven.org/maven2/io/prometheus/jmx/jmx_prometheus_javaagent/0.20.0/jmx_prometheus_javaagent-0.20.0.jar"
fi

if [ -f /jmx/kafka-17x.yaml ] && [ ! -f "$JMX_DIR/kafka-17x.yaml" ]; then
  cp /jmx/kafka-17x.yaml "$JMX_DIR/kafka-17x.yaml"
fi

# ─── ZooKeeper Mode Config (Kafka 3.9 still supports ZK mode) ─────────────────
# KRaft (KRaft) requires kafka-storage.sh format which needs running ZooKeeper/KRaft quorum.
# Simplest reliable path: use ZooKeeper mode.
SERVER_PROPS="/opt/kafka/config/server.properties"
HOSTNAME=$(hostname)

# Only patch if not already configured (idempotent for restarts)
if ! grep -q "^# __ZK_configured__" "$SERVER_PROPS" 2>/dev/null; then
  echo "Configuring ZooKeeper mode in server.properties..."

  # 1. Keep broker.id as-is (default 0, we override per node)
  sed -i "s/^broker\.id=.*/broker.id=${KAFKA_NODE_ID:-0}/" "$SERVER_PROPS"

  # 2. Set ZK connect string
  sed -i "s/^zookeeper.connect=.*/zookeeper.connect=zookeeper:2181/" "$SERVER_PROPS"

  # 3. Uncomment and set listeners
  # Use KAFKA_ADVERTISED_HOST if set (for Swarm service names), otherwise fall back to hostname
  ADVERTISED_HOST="${KAFKA_ADVERTISED_HOST:-${HOSTNAME}}"
  sed -i "s/^#*listeners=.*/listeners=PLAINTEXT:\\/\\/:9092/" "$SERVER_PROPS"
  sed -i "s/^#*advertised\.listeners=.*/advertised.listeners=PLAINTEXT:\\/\\/${ADVERTISED_HOST}:9092/" "$SERVER_PROPS"

  # 4. Mark as configured
  sed -i '1s/^/# __ZK_configured__\n/' "$SERVER_PROPS"
  echo "ZK mode config applied."
else
  echo "ZK mode already configured, skipping."
fi

# ─── Clean stale ZK broker registration ────────────────────────────────────
# In Swarm, containers restart with the same broker.ID but ZK's ephemeral
# node may still exist from the old container (session not yet expired).
# Deleting the stale node before startup avoids NodeExistsException.
if [ -n "${KAFKA_NODE_ID:-}" ]; then
  echo "Cleaning stale ZK broker registration for broker.id=${KAFKA_NODE_ID}..."
  echo "delete /brokers/ids/${KAFKA_NODE_ID}" | \
    /opt/kafka/bin/zookeeper-shell.sh zookeeper:2181 2>/dev/null || true
fi

# ─── Set shorter ZK session timeout for faster Swarm failover ──────────────
# Default is 18s; lower to 10s so a replaced container's ephemeral node
# expires faster, reducing window where a new container gets NodeExists.
KAFKA_OPTS="${KAFKA_OPTS} -Dzookeeper.session.timeout.ms=10000 -Dzookeeper.connection.timeout.ms=8000"
export KAFKA_OPTS

# Build KAFKA_OPTS with JMX agent and heap settings
export KAFKA_OPTS="-Xmx1g -Xms1g -javaagent:${JMX_JAR}=9999:${JMX_DIR}/kafka-17x.yaml"

exec /opt/kafka/bin/kafka-server-start.sh /opt/kafka/config/server.properties
