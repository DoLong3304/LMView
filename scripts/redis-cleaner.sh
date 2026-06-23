#!/bin/bash
# scripts/redis-cleaner.sh
# Periodically purges stale candle/ticker keys from the Redis Sentinel cluster.
# Safe to run on the manager or worker; uses docker exec to talk to redis-master.

set -euo pipefail

REDIS_MASTER_CONTAINER=$(docker ps --filter name=redis-master -q | head -1)
if [ -z "${REDIS_MASTER_CONTAINER}" ]; then
    echo "[redis-cleaner] redis-master container not found" >&2
    exit 1
fi

# 7 days in milliseconds
TTL_MS=604800000
NOW_MS=$(date +%s%3N)

cleanup_pattern() {
    local pattern="$1"
    docker exec "${REDIS_MASTER_CONTAINER}" redis-cli --scan --pattern "${pattern}" \
        | while IFS= read -r key; do
            [ -z "${key}" ] && continue
            ts=$(docker exec "${REDIS_MASTER_CONTAINER}" redis-cli hget "${key}" event_time 2>/dev/null || echo 0)
            if [ "${ts:-0}" = "0" ]; then
                # No timestamp → keep
                continue
            fi
            age=$((NOW_MS - ts))
            if [ "${age}" -gt "${TTL_MS}" ]; then
                docker exec "${REDIS_MASTER_CONTAINER}" redis-cli del "${key}" >/dev/null
                echo "[redis-cleaner] deleted ${key} (age=${age}ms)"
            fi
        done
}

echo "[redis-cleaner] starting at $(date -u +%FT%TZ)"
cleanup_pattern "ticker:latest:*"
cleanup_pattern "candle:1m:*"
cleanup_pattern "candle:1s:*"
cleanup_pattern "trade:latest:*"
echo "[redis-cleaner] done"