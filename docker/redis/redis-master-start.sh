#!/bin/sh
# LMView Redis Master Startup Script
#
# PROBLEM: After Sentinel failover or OOM restart, Redis may start with stale
# replication config (as slave) from previous state in RDB/AOF files.
#
# SOLUTION: Force redis-master to always start as MASTER, clearing any
# replica configuration. This prevents split-brain where all nodes think
# they're slaves pointing to dead masters.
#
# This script runs BEFORE redis-server starts.

set -e

echo "[redis-master-start] Ensuring master role on startup..."

# If this is redis-master container (not replica), clear any replication state
if [ "$(hostname)" = "redis-master" ]; then
  echo "[redis-master-start] This is redis-master - will start as MASTER"

  # Create a startup config that overrides any saved replication state
  cat > /tmp/redis-master-override.conf << 'EOF'
# Force master role - ignore any saved replicaof config
replicaof NO ONE

# Ensure we accept writes immediately
replica-read-only no

# Disable persistence during initial startup to avoid loading stale state
save ""
EOF

  # Merge with base config
  if [ -f /etc/redis/redis.conf ]; then
    cat /etc/redis/redis.conf /tmp/redis-master-override.conf > /tmp/redis-final.conf
  else
    cp /tmp/redis-master-override.conf /tmp/redis-final.conf
  fi

  echo "[redis-master-start] Starting redis-server as MASTER..."
  exec redis-server /tmp/redis-final.conf "$@"
else
  # This is a replica - start normally with replicaof from command line
  echo "[redis-master-start] Starting as replica (replicaof from docker-compose command)..."
  exec redis-server "$@"
fi
