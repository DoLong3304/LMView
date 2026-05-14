"""
Market metrics service — business logic for market overview, gainers/losers.
"""
from datetime import datetime
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


# In-memory cache for market metrics (will be replaced with Redis)
_market_cache = {
    "metrics": [],
    "summary": {},
    "top_gainers": [],
    "top_losers": [],
    "last_update": None
}


def get_overview() -> dict:
    """Return overall market overview summary."""
    summary = dict(_market_cache.get("summary", {}))
    summary["last_update"] = _market_cache.get("last_update")
    return summary


def get_metrics(limit: int = 100, sort_by: str = "rank") -> dict:
    """Return sorted market metrics for all symbols."""
    metrics = list(_market_cache.get("metrics", []))

    sort_keys = {
        "change_24h_pct": ("change_24h_pct", True),
        "volume_24h": ("volume_24h", True),
        "market_cap": ("market_cap", True),
        "rank": ("rank", False),
    }
    key_name, reverse = sort_keys.get(sort_by, ("rank", False))
    metrics.sort(key=lambda x: x.get(key_name, 0), reverse=reverse)

    return {"total": len(metrics), "metrics": metrics[:limit]}


def get_top_gainers(limit: int = 10, timeframe: str = "24h") -> dict:
    """Return top gaining symbols for given timeframe."""
    change_field = f"change_{timeframe}_pct"
    metrics = _market_cache.get("metrics", [])
    gainers = sorted(
        [m for m in metrics if m.get(change_field, 0) > 0],
        key=lambda x: x.get(change_field, 0),
        reverse=True,
    )[:limit]
    return {"timeframe": timeframe, "gainers": gainers}


def get_top_losers(limit: int = 10, timeframe: str = "24h") -> dict:
    """Return top losing symbols for given timeframe."""
    change_field = f"change_{timeframe}_pct"
    metrics = _market_cache.get("metrics", [])
    losers = sorted(
        [m for m in metrics if m.get(change_field, 0) < 0],
        key=lambda x: x.get(change_field, 0),
    )[:limit]
    return {"timeframe": timeframe, "losers": losers}


def get_symbol_metrics(symbol: str) -> Optional[dict]:
    """Return metrics for a single symbol, or None if not found."""
    symbol_upper = symbol.upper()
    metrics = _market_cache.get("metrics", [])
    return next(
        (m for m in metrics if m.get("symbol", "").upper() == symbol_upper),
        None,
    )


def get_heatmap(limit: int = 100) -> dict:
    """Return simplified heatmap data sorted by market cap."""
    metrics = _market_cache.get("metrics", [])
    heatmap = sorted(metrics, key=lambda x: x.get("market_cap", 0), reverse=True)[:limit]
    return {
        "symbols": [
            {
                "symbol": m.get("symbol"),
                "change_24h_pct": m.get("change_24h_pct", 0),
                "market_cap": m.get("market_cap", 0),
                "volume_24h": m.get("volume_24h", 0),
            }
            for m in heatmap
        ]
    }


def update_market_cache(metrics: List[dict], summary: dict):
    """Update in-memory market cache (called by background task)."""
    metrics_sorted = sorted(metrics, key=lambda x: x.get("rank", 999))

    top_gainers = sorted(
        [m for m in metrics if m.get("change_24h_pct", 0) > 0],
        key=lambda x: x.get("change_24h_pct", 0),
        reverse=True,
    )[:10]

    top_losers = sorted(
        [m for m in metrics if m.get("change_24h_pct", 0) < 0],
        key=lambda x: x.get("change_24h_pct", 0),
    )[:10]

    _market_cache["metrics"] = metrics_sorted
    _market_cache["summary"] = summary
    _market_cache["top_gainers"] = top_gainers
    _market_cache["top_losers"] = top_losers
    _market_cache["last_update"] = datetime.now().isoformat()

    logger.info("Updated market cache with %d symbols", len(metrics))
