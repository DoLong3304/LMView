"""
FastAPI application entry point.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import CORS_ORIGINS
from backend.core.database import close_all
from backend.core.postgres import init_pg_pool, close_pg_pool, run_migration
from backend.api import (
    health,
    ticker,
    klines,
    historical,
    orderbook,
    trades,
    symbols,
    indicators,
    websocket,
    market_overview,
    market,
    news,
    auth,
    ai,
)
from backend.tasks.news_fetcher import news_fetcher
from backend.tasks.market_fetcher import market_fetcher

import logging
import os

logger = logging.getLogger("backend.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize PostgreSQL pool
    await init_pg_pool()

    # Run Phase 0 migration if flag is set
    if os.environ.get("RUN_MIGRATIONS", "").lower() in ("1", "true", "yes"):
        migration_path = os.path.join(
            os.path.dirname(__file__), "migrations", "001_phase0_schema.sql"
        )
        if os.path.exists(migration_path):
            try:
                await run_migration(migration_path)
                logger.info("Phase 0 migration applied successfully")
            except Exception:
                logger.exception("Failed to apply Phase 0 migration")

    # Start background tasks
    await news_fetcher.start()
    await market_fetcher.start()

    yield

    # Stop background tasks
    await news_fetcher.stop()
    await market_fetcher.stop()
    await close_all()
    await close_pg_pool()


app = FastAPI(title="LMView API", version="0.15.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics instrumentation (optional — requires prometheus-fastapi-instrumentator)
try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app)
except ImportError:
    pass

for router_module in (
    health,
    ticker,
    klines,
    historical,
    orderbook,
    trades,
    symbols,
    indicators,
    websocket,
    market_overview,
    market,
    news,
    auth,
    ai,
):
    app.include_router(router_module.router)
