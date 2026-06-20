#!/usr/bin/env bash
# Cron wrapper: refresh Redis 1m candle cache from Binance REST.
#
# Background: producer's WS path is permanently 403'd from this AWS region
# (Binance ELB geofencing). This script is the REST fallback that keeps
# the Redis candle:1m:* cache fresh so the frontend chart doesn't snap.
#
# Long-term replacement: a proper Swarm kline-poller service (see
# docs/system/13-caveats.md DP-2). This cron is the stopgap.
#
# Install (runs every 2 min):
#   */2 * * * * /mnt/efs/LMView/scripts/cron_refresh_klines.sh >> /var/log/lmview-kline-refresh.log 2>&1
#
# Tunables via env:
#   KLINE_REFRESH_SYMBOLS  comma list, default = top 30 by 24h quote vol
#   KLINE_REFRESH_LIMIT    1m candles per symbol (default 100)
#   KLINE_REFRESH_TOP      top-N if SYMBOLS unset (default 30)

set -euo pipefail

REPO="/mnt/efs/LMView"
SCRIPT="${REPO}/scripts/refresh_redis_klines.py"

# Find the running fastapi-prod container (has redis-py + Sentinel env + EFS).
CID="$(docker ps -q -f name=fastapi-prod | head -1 || true)"
if [[ -z "${CID}" ]]; then
  echo "$(date -Is) ERR: no fastapi-prod container running; skipping."
  exit 0  # not fatal — cron will retry next interval
fi

SYMBOLS="${KLINE_REFRESH_SYMBOLS:-}"
LIMIT="${KLINE_REFRESH_LIMIT:-100}"
TOP="${KLINE_REFRESH_TOP:-30}"

# Copy script fresh each run in case it was updated on EFS.
docker cp "${SCRIPT}" "${CID}:/tmp/refresh_redis_klines.py" >/dev/null

echo "$(date -Is) refresh start (cid=${CID:0:12} top=${TOP} limit=${LIMIT})"
if [[ -n "${SYMBOLS}" ]]; then
  docker exec -e LOG_LEVEL=WARNING "${CID}" \
    python /tmp/refresh_redis_klines.py --symbols "${SYMBOLS}" --limit "${LIMIT}" \
    || echo "$(date -Is) WARN: refresh exited non-zero"
else
  docker exec -e LOG_LEVEL=WARNING "${CID}" \
    python /tmp/refresh_redis_klines.py --top "${TOP}" --limit "${LIMIT}" \
    || echo "$(date -Is) WARN: refresh exited non-zero"
fi
echo "$(date -Is) refresh done"
