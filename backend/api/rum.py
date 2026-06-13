"""
Real User Monitoring (RUM) ingest endpoint.

Receives batched frontend error + performance events from
``frontend/src/utils/rum.ts`` and translates them into Prometheus
metrics so the A9.1 (Frontend JS error rate) alert and
``frontend-rum`` panels in the executive-overview dashboard can
chart them.

Metrics updated (see ``backend/api/metrics.py``):
  - ``frontend_rum_errors_total{type, source}`` — error events
  - ``frontend_rum_page_loads_total{route}`` — pageview events
  - ``frontend_rum_lcp_seconds{route}`` — Largest Contentful Paint
  - ``frontend_rum_inp_seconds{route}`` — Interaction to Next Paint

Notes
-----
* The endpoint is intentionally cheap: it accepts a JSON body with
  ``events`` and writes to in-process counters. We don't persist
  events to PostgreSQL — those are ephemeral by design (RUM
  sampling would defeat the purpose).
* A real-world deployment would also want rate limiting and a
  per-IP token-bucket to prevent log spam attacks, but that lives
  in the API gateway layer (see ``A10.2 Rate limit hit`` in
  ``docs/dataflow_analysis_and_observability_plan.md``).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from backend.api.metrics import (
    record_frontend_rum_error,
    record_frontend_rum_lcp,
    record_frontend_rum_inp,
    record_frontend_rum_pageview,
)

logger = logging.getLogger("backend.api.rum")

router = APIRouter(prefix="/api/rum", tags=["rum"])


class RumEvent(BaseModel):
    type: str
    source: str
    route: str
    message: str | None = None
    stack: str | None = None
    lcp: float | None = None
    inp: float | None = None
    ts: int


class RumBatch(BaseModel):
    events: List[RumEvent] = Field(default_factory=list)


@router.post("/events", include_in_schema=False)
async def receive_rum_events(batch: RumBatch, request: Request) -> Dict[str, int]:
    """Accept a batch of RUM events from the frontend.

    Returns the number of events that were successfully recorded
    so the client can retry the rest on a 5xx.
    """
    client_ip = request.client.host if request.client else "unknown"
    recorded = 0
    for ev in batch.events:
        try:
            if ev.type == "error":
                record_frontend_rum_error(
                    error_type=ev.source,
                    source="browser",
                )
            elif ev.type == "pageview":
                record_frontend_rum_pageview(route=ev.route)
            elif ev.type == "perf":
                if ev.lcp is not None:
                    record_frontend_rum_lcp(route=ev.route, lcp_sec=ev.lcp)
                if ev.inp is not None:
                    record_frontend_rum_inp(route=ev.route, inp_sec=ev.inp)
            recorded += 1
        except Exception as exc:  # never fail the whole batch
            logger.warning("RUM event dropped (ip=%s): %s", client_ip, exc)
    return {"received": len(batch.events), "recorded": recorded}
