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
    screener,
    rum,
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


app = FastAPI(title="LMView API", version="0.24.4", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-process rate limiter (A10.2). Nginx still enforces a per-IP limit
# at the edge; this is defence-in-depth. Disable by setting
# ``RATE_LIMIT_PER_MINUTE=0`` in the environment.
if os.environ.get("RATE_LIMIT_PER_MINUTE", "200") != "0":
    from backend.middleware.rate_limit import RateLimitMiddleware
    app.add_middleware(RateLimitMiddleware)

# Prometheus metrics instrumentation (optional — requires prometheus-fastapi-instrumentator)
try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app)
except ImportError:
    pass


# ── Custom Prometheus endpoints (Phase 5: dataflow plan) ──────────────────────────
# ``prometheus.yml`` declares two extra scrape jobs that pull from
# ``fastapi:8000`` on non-default paths:
#   - /metrics-custom  — WebSocket / multi-source / cache metrics
#                         (declared in ``backend/api/metrics.py``)
#   - /metrics-ai      — AI / RAG / scope-gate / cost metrics
#                         (declared in ``backend/services/ai/metrics.py``)
# We expose both by serialising the metrics from the corresponding
# modules and selecting only the time series whose name belongs to that
# module. The output is plain text in the standard Prometheus
# exposition format so Prometheus can scrape it without extra glue.
from fastapi import Response
from prometheus_client import (
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
    multiprocess,
)
from prometheus_client.metrics_core import Metric


def _serialize_module_metrics(metric_names: set[str]) -> bytes:
    """Render the metrics whose name is in ``metric_names`` to text.

    We can't easily partition the global ``REGISTRY`` by module (the
    registry only knows about metric *names*, not which module
    declared them), so we read everything from the registry and drop
    anything that doesn't match. This is a small overhead per scrape
    (Prometheus scrapes every 10–15s) and keeps the implementation
    simple.
    """
    from prometheus_client import REGISTRY as _DEFAULT_REGISTRY
    out_lines: list[str] = []
    for metric in _DEFAULT_REGISTRY.collect():
        if metric.name not in metric_names:
            continue
        out_lines.append(f"# HELP {metric.name} {metric.documentation}")
        out_lines.append(f"# TYPE {metric.name} {metric.type}")
        for sample in metric.samples:
            label_str = ""
            if sample.labels:
                pairs = ",".join(
                    f'{k}="{v}"' for k, v in sample.labels.items()
                )
                label_str = "{" + pairs + "}"
            out_lines.append(f"{sample.name}{label_str} {sample.value}")
    return ("\n".join(out_lines) + "\n").encode("utf-8")


def _collect_metric_names(module) -> set[str]:
    """Find every Prometheus metric a module has declared.

    Heuristic: walk the module's attributes and pick out the
    ``Counter`` / ``Gauge`` / ``Histogram`` / ``Summary`` / ``Info``
    instances. The metric name comes from the instance's ``_name``
    attribute.
    """
    from prometheus_client.metrics import (
        Counter as _Counter, Gauge as _Gauge,
        Histogram as _Histogram, Summary as _Summary, Info as _Info,
    )
    names: set[str] = set()
    for attr_name in dir(module):
        attr = getattr(module, attr_name, None)
        if isinstance(attr, (_Counter, _Gauge, _Histogram, _Summary, _Info)):
            names.add(attr._name)
    return names


# Pre-compute the name sets so we don't walk the modules on every scrape.
try:
    from backend.api import metrics as api_metrics_module
    _CUSTOM_METRIC_NAMES = _collect_metric_names(api_metrics_module)
except Exception as e:  # pragma: no cover - defensive
    _CUSTOM_METRIC_NAMES = set()
    logger.warning("Could not collect custom metric names: %s", e)

try:
    from backend.services.ai import metrics as ai_metrics_module
    _AI_METRIC_NAMES = _collect_metric_names(ai_metrics_module)
except Exception as e:  # pragma: no cover - defensive
    _AI_METRIC_NAMES = set()
    logger.warning("Could not collect AI metric names: %s", e)


@app.get("/metrics-custom", include_in_schema=False)
async def metrics_custom() -> Response:
    """WebSocket / multi-source / cache metrics (see ``backend/api/metrics.py``)."""
    return Response(
        content=_serialize_module_metrics(_CUSTOM_METRIC_NAMES),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/metrics-ai", include_in_schema=False)
async def metrics_ai() -> Response:
    """AI / RAG / scope-gate / cost metrics (see ``backend/services/ai/metrics.py``)."""
    return Response(
        content=_serialize_module_metrics(_AI_METRIC_NAMES),
        media_type=CONTENT_TYPE_LATEST,
    )


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
    screener,
    rum,
):
    app.include_router(router_module.router)
