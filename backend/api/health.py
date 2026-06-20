"""
Health check API endpoint.
"""

import asyncio
import time
from datetime import datetime, timezone

from fastapi import APIRouter

from backend.core.database import get_redis, get_influx, get_trino_connection
from backend.core.postgres import pg_health_check
from backend.core.redis_sentinel import get_redis_health

router = APIRouter(prefix="/api", tags=["health"])

APP_START_TS = time.time()


async def _check_with_timeout(check_fn, timeout: float = 5.0, default=None):
    """Run a health check with a per-component timeout (BB-5 fix)."""
    try:
        return await asyncio.wait_for(check_fn(), timeout=timeout)
    except asyncio.TimeoutError:
        return default if default is not None else {"status": "timeout"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/health")
async def health():
    """Check connectivity to all backend dependencies and report overall status."""
    overall_start = time.perf_counter()
    checks = {}
    latencies = {}

    # PostgreSQL health (with 5s timeout)
    pg_start = time.perf_counter()
    pg_check = await _check_with_timeout(
        lambda: pg_health_check(), timeout=5.0,
        default={"status": "timeout", "detail": "postgres health check timed out"},
    )
    checks["postgresql"] = pg_check
    latencies["postgresql_ms"] = round((time.perf_counter() - pg_start) * 1000, 2)

    # Redis Sentinel cluster health (with 5s timeout)
    redis_start = time.perf_counter()
    redis_result = await _check_with_timeout(lambda: _check_redis(), timeout=5.0)
    checks["redis"] = redis_result
    latencies["redis_ms"] = round((time.perf_counter() - redis_start) * 1000, 2)

    # InfluxDB health (with 5s timeout)
    influx_start = time.perf_counter()
    influx_result = await _check_with_timeout(lambda: _check_influx(), timeout=5.0)
    checks["influxdb"] = influx_result
    latencies["influxdb_ms"] = round((time.perf_counter() - influx_start) * 1000, 2)

    # Trino health (with 5s timeout — BB-5: prevents hung Trino from blocking health)
    trino_start = time.perf_counter()
    trino_result = await _check_with_timeout(lambda: _check_trino(), timeout=5.0)
    checks["trino"] = trino_result
    latencies["trino_ms"] = round((time.perf_counter() - trino_start) * 1000, 2)

    # Determine overall status
    # Status check: handle both old-style strings and new-style dicts
    def _check_ok(val, ok_values=("ok", "healthy")):
        if isinstance(val, dict):
            return val.get("status") in ok_values
        return val in ok_values

    redis_ok = _check_ok(checks.get("redis"))
    influx_ok = _check_ok(checks.get("influxdb"))
    trino_ok = _check_ok(checks.get("trino"))
    pg_ok = _check_ok(checks.get("postgresql"))

    status = "ok" if (redis_ok and influx_ok and trino_ok and pg_ok) else "degraded"

    total_latency_ms = round((time.perf_counter() - overall_start) * 1000, 2)
    return {
        "status": status,
        "checks": checks,
        "latency_ms": latencies,
        "total_latency_ms": total_latency_ms,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "uptime_sec": int(time.time() - APP_START_TS),
    }


async def _check_redis():
    """Check Redis Sentinel cluster health (BB-5)."""
    redis_health_info = await get_redis_health()
    r = await get_redis()
    await r.ping()
    return redis_health_info


async def _check_influx():
    """Check InfluxDB connectivity (BB-5)."""
    get_influx().ping()
    return "ok"


async def _check_trino():
    """Check Trino connectivity (BB-5)."""
    conn = get_trino_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        return "ok"
    finally:
        conn.close()
