"""
Indicators API — expanded endpoints with freshness metadata.

Business logic lives in ``backend.services.indicator_service``.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.services.indicator_service import (
    get_indicator_snapshot,
    get_indicator_summary,
    get_supported_indicators,
)

router = APIRouter(prefix="/api", tags=["indicators"])


@router.get("/indicators/supported")
async def list_supported_indicators():
    """List all supported indicators with their default parameters."""
    indicators = get_supported_indicators()
    return {
        "indicators": [ind.model_dump() for ind in indicators],
        "total": len(indicators),
    }


@router.get("/indicators/{symbol}")
async def get_indicators(
    symbol: str,
    exchange: str = Query("binance", description="Exchange name"),
):
    """
    Get latest indicator values for a symbol.

    Returns available indicators from Redis with freshness metadata.
    Extended indicators (RSI, MACD, etc.) are listed as unavailable
    until the pipeline computes them.
    """
    snapshot = await get_indicator_snapshot(symbol, exchange)

    if snapshot.source == "unavailable":
        raise HTTPException(404, f"No indicator data for {symbol}")

    return snapshot.model_dump()


@router.get("/indicators/{symbol}/summary")
async def get_indicator_summary_endpoint(
    symbol: str,
    exchange: str = Query("binance", description="Exchange name"),
):
    """Compact indicator summary for AI context."""
    summary = await get_indicator_summary(symbol, exchange)
    return summary.model_dump()
