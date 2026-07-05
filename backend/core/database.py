from __future__ import annotations

from redis.asyncio import Redis

from influxdb_client import InfluxDBClient
import trino

from backend.core.config import (
    INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG,
    TRINO_HOST, TRINO_PORT,
)
from backend.core.redis_sentinel import get_redis_master, get_redis_replica, get_redis_sentinel

_influx: InfluxDBClient | None = None


async def get_redis() -> Redis:
    """
    Get Redis client for general use.

    Reads and writes go to master directly. Replica reads were too slow
    to catch up with high-frequency ticker/1s/1m writes, causing stale
    data on realtime endpoints (/api/ticker, WS /stream/all, 1s/1m
    candles) while 5m-1w aggregates (read from Influx/Trino) still
    looked fine. Master writes only scale the same way since they all
    target the same Redis instance.

    For explicit read/write splitting, use:
    - get_redis_master() for writes (now same as get_redis)
    - get_redis_replica() for read-only access (analytics, exports)
    """
    return await get_redis_master()


def get_influx() -> InfluxDBClient:
    global _influx
    if _influx is None:
        _influx = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    return _influx


def get_trino_connection():
    return trino.dbapi.connect(
        host=TRINO_HOST,
        port=TRINO_PORT,
        user="fastapi",
        catalog="iceberg_catalog",
        schema="crypto_lakehouse",
    )


async def close_all():
    global _influx

    # Close Redis Sentinel connections
    sentinel = get_redis_sentinel()
    await sentinel.close()

    if _influx:
        _influx.close()
        _influx = None
