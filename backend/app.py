"""
FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from pathlib import Path
import asyncio

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
    settings,
    admin,
)
from backend.services.admin_bootstrap_service import ensure_default_admin
from backend.tasks.news_fetcher import news_fetcher
from backend.tasks.market_fetcher import market_fetcher
from backend.services.sentiment_service import batch_score_unscored_articles

import logging
import os

logger = logging.getLogger("backend.app")


async def sentiment_score_loop():
    while True:
        try:
            await asyncio.sleep(600)
            scored = await batch_score_unscored_articles(batch_size=20)
            logger.info("Sentiment loop scored %d articles", scored)
        except Exception:
            logger.exception("Sentiment loop failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize PostgreSQL pool
    await init_pg_pool()

    # Run ordered SQL migrations if flag is set
    if os.environ.get("RUN_MIGRATIONS", "").lower() in ("1", "true", "yes"):
        migration_dir = Path(__file__).resolve().parent / "migrations"
        for migration_path in sorted(migration_dir.glob("*.sql")):
            try:
                await run_migration(str(migration_path))
                logger.info("Migration applied successfully: %s", migration_path.name)
            except Exception:
                logger.exception("Failed to apply migration: %s", migration_path.name)

    await ensure_default_admin()

    # Start background tasks
    await news_fetcher.start()
    await market_fetcher.start()
    sentiment_task = asyncio.create_task(sentiment_score_loop())

    yield

    # Stop background tasks
    sentiment_task.cancel()
    try:
        await sentiment_task
    except asyncio.CancelledError:
        pass
    await news_fetcher.stop()
    await market_fetcher.stop()
    await close_all()
    await close_pg_pool()


app = FastAPI(title="LMView API", version="0.18.0", lifespan=lifespan)

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
    settings,
    admin,
):
    app.include_router(router_module.router)
