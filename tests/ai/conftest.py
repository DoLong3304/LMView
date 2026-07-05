"""conftest for AI RAG quality tests.

Provides fixtures that skip tests requiring a database when
the database is not available.
"""
from __future__ import annotations

import os

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers used by AI tests."""
    config.addinivalue_line("markers", "requires_db: test needs PostgreSQL/RAG data")


@pytest.fixture(scope="session")
def db_available() -> bool:
    """Check if PostgreSQL is available for RAG tests.

    Uses a one-off asyncpg connection instead of ``get_pg_pool()``.
    ``get_pg_pool()`` caches a pool bound to the event loop used by
    ``asyncio.run()`` here; pytest-asyncio later uses a different loop,
    producing ``RuntimeError: Event loop is closed`` in RAG tests.
    """
    import asyncio

    import asyncpg

    async def _check() -> bool:
        conn = None
        try:
            conn = await asyncpg.connect(
                user=os.environ.get("POSTGRES_USER", "iceberg"),
                password=os.environ.get("POSTGRES_PASSWORD", ""),
                database=os.environ.get("POSTGRES_LMVIEW_DB", "iceberg_catalog"),
                host=os.environ.get("POSTGRES_HOST", "postgres"),
                port=int(os.environ.get("POSTGRES_PORT", "5432")),
                timeout=3,
            )
            await conn.execute("SELECT 1")
            return True
        except Exception:
            return False
        finally:
            if conn is not None:
                await conn.close()

    return asyncio.run(_check())

@pytest.fixture(autouse=True)
def skip_if_no_db(request, db_available):
    """Automatically skip RAG tests when database is unavailable.

    Only applies to tests in ``TestRAGRetrievalQuality`` and
    ``TestRAGRetrievalMetadata`` classes.
    """
    marker = request.node.get_closest_marker("requires_db")
    if marker is not None and not db_available:
        pytest.skip("Database unavailable — skipping RAG test")
