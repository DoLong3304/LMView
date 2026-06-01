"""
Async PostgreSQL connection pool for LMView.

Uses asyncpg for non-blocking database access.
Connection parameters come from environment variables.
"""
from __future__ import annotations

import hashlib
import logging
import os
from typing import Optional

logger = logging.getLogger("backend.core.postgres")

# Lazy import: asyncpg is optional for test environments
_pool = None


def _get_pg_dsn() -> str:
    """Build PostgreSQL DSN from environment variables."""
    user = os.environ.get("POSTGRES_USER", "iceberg")
    password = os.environ.get("POSTGRES_PASSWORD", "")
    host = os.environ.get("POSTGRES_HOST", "postgres")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_LMVIEW_DB", "iceberg_catalog")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


async def init_pg_pool() -> None:
    """Initialize the global asyncpg connection pool."""
    global _pool
    if _pool is not None:
        return

    try:
        import asyncpg
    except ImportError:
        logger.warning(
            "asyncpg not installed — PostgreSQL features disabled. "
            "Install with: pip install asyncpg"
        )
        return

    dsn = _get_pg_dsn()
    # Log DSN without password
    safe_dsn = dsn.split("@")[-1] if "@" in dsn else dsn
    logger.info("Connecting to PostgreSQL: %s", safe_dsn)

    try:
        _pool = await asyncpg.create_pool(
            dsn,
            min_size=2,
            max_size=10,
            command_timeout=30,
        )
        logger.info("PostgreSQL connection pool initialized")
    except Exception:
        logger.exception("Failed to initialize PostgreSQL pool")
        _pool = None


async def get_pg_pool():
    """Return the asyncpg pool, or None if unavailable."""
    return _pool


async def close_pg_pool() -> None:
    """Close the PostgreSQL connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("PostgreSQL connection pool closed")


async def pg_health_check() -> dict:
    """Check PostgreSQL connectivity and return status dict."""
    if _pool is None:
        return {"status": "unavailable", "error": "Pool not initialized"}
    try:
        async with _pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            if result == 1:
                return {"status": "healthy"}
            return {"status": "unhealthy", "error": "Unexpected result"}
    except Exception as exc:
        return {"status": "unhealthy", "error": str(exc)}


async def run_migration(sql_path: str) -> None:
    """Execute an SQL migration file idempotently."""
    if _pool is None:
        logger.warning("Cannot run migration — PostgreSQL pool not available")
        return

    import pathlib
    sql = pathlib.Path(sql_path).read_text(encoding="utf-8")

    async with _pool.acquire() as conn:
        await conn.execute(sql)
    logger.info("Migration applied: %s", sql_path)


def hash_token(token: str) -> str:
    """Hash a session token using SHA-256 for storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
