#!/bin/sh
set -e

echo "[sentinel-entrypoint] Starting Sentinel initialization..."

# Get this container's hostname and IP for sentinel announcement
MY_HOSTNAME=$(hostname)
MY_IP=$(hostname -i 2>/dev/null || getent hosts $MY_HOSTNAME | awk '{print $1}')
echo "[sentinel-entrypoint] This sentinel: $MY_HOSTNAME ($MY_IP)"

# Wait for redis-master to be resolvable (max 60 seconds)
echo "[sentinel-entrypoint] Waiting for redis-master to be resolvable..."
count=0
until getent hosts redis-master > /dev/null 2>&1; do
    count=$((count + 1))
    if [ $count -ge 30 ]; then
        echo "[sentinel-entrypoint] ERROR: redis-master not resolvable after 60s"
        exit 1
    fi
    sleep 2
done

# Get IP address of redis-master
MASTER_IP=$(getent hosts redis-master | awk '{ print $1 }')
echo "[sentinel-entrypoint] redis-master resolved to IP: $MASTER_IP"

# Wait for master to actually respond to PING (max 30 seconds)
echo "[sentinel-entrypoint] Waiting for redis-master to respond to PING..."
count=0
until redis-cli -h redis-master -p 6379 ping > /dev/null 2>&1; do
    count=$((count + 1))
    if [ $count -ge 15 ]; then
        echo "[sentinel-entrypoint] ERROR: redis-master not responding after 30s"
        exit 1
    fi
    sleep 2
done
echo "[sentinel-entrypoint] redis-master is responding"

# Copy base sentinel.conf and add announce-ip directive
cp /etc/redis/sentinel.conf /tmp/sentinel.conf

# Add announce-ip and announce-port so other sentinels can reach us correctly
cat >> /tmp/sentinel.conf <<EOF

# Announce this sentinel's actual IP (critical for Docker Swarm overlay)
sentinel announce-ip $MY_IP
sentinel announce-port 26379
EOF

echo "[sentinel-entrypoint] Starting sentinel with config:"
cat /tmp/sentinel.conf

# Start Redis Sentinel
exec redis-sentinel /tmp/sentinel.conf

