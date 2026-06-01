"""
Pydantic models for chart context DTO shared between frontend and backend.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.models.common import DataFreshness


class CandleSummary(BaseModel):
    """Compact candle summary for context transfer."""
    open_time: Optional[int] = None  # epoch ms
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[float] = None


class IndicatorValue(BaseModel):
    """Single indicator latest value."""
    name: str
    value: Optional[float] = None
    signal: Optional[str] = None  # bullish, bearish, neutral
    params: Dict[str, Any] = Field(default_factory=dict)


class OrderBookSummary(BaseModel):
    """Compact order book summary for AI context."""
    best_bid: Optional[float] = None
    best_ask: Optional[float] = None
    spread: Optional[float] = None
    bid_depth: Optional[float] = None
    ask_depth: Optional[float] = None
    imbalance: Optional[float] = None  # (bid_depth - ask_depth) / total
    source: str = "unknown"
    freshness: Optional[DataFreshness] = None


class TradeSummary(BaseModel):
    """Compact trade summary for AI context."""
    latest_price: Optional[float] = None
    tick_count: int = 0
    volume_sum: Optional[float] = None
    inferred_direction: Optional[str] = None  # up, down, flat
    data_type: str = "ticker_derived"
    is_true_trade_tape: bool = False
    source: str = "unknown"
    freshness: Optional[DataFreshness] = None


class NewsSummary(BaseModel):
    """Compact news summary for AI context."""
    article_count: int = 0
    avg_sentiment: Optional[float] = None
    top_headline: Optional[str] = None
    freshness: Optional[DataFreshness] = None


class MarketOverviewSummary(BaseModel):
    """Compact market overview summary for AI context."""
    btc_dominance: Optional[float] = None
    total_market_cap: Optional[float] = None
    fear_greed_index: Optional[int] = None
    is_placeholder: bool = True
    freshness: Optional[DataFreshness] = None


class VisibleRange(BaseModel):
    """Chart visible time range."""
    start: Optional[int] = None  # epoch seconds
    end: Optional[int] = None  # epoch seconds


class ChartContextDTO(BaseModel):
    """
    Shared chart context contract between frontend and backend.

    Frontend builds this from current chart state.
    Backend normalizes/validates and optionally enriches missing fields.
    """
    # Core chart state
    symbol: str
    exchange: str = "binance"
    timeframe: str = "1m"
    chart_type: Optional[str] = "candles"  # candles, line, area, bars

    # Visible range
    visible_range: Optional[VisibleRange] = None

    # Active indicators
    selected_indicators: List[str] = Field(default_factory=list)
    indicator_values: List[IndicatorValue] = Field(default_factory=list)

    # Active drawings
    active_drawings: List[Dict[str, Any]] = Field(default_factory=list)

    # Candle data (compact — not full arrays)
    latest_candle: Optional[CandleSummary] = None
    recent_candles_summary: Optional[Dict[str, Any]] = None

    # Market data summaries
    orderbook_summary: Optional[OrderBookSummary] = None
    trades_summary: Optional[TradeSummary] = None
    news_summary: Optional[NewsSummary] = None
    market_overview_summary: Optional[MarketOverviewSummary] = None

    # Freshness metadata
    data_freshness: Dict[str, DataFreshness] = Field(default_factory=dict)

    # Versioning
    frontend_context_version: str = "1.0.0"
    backend_context_version: Optional[str] = None


class ChartContextResponse(BaseModel):
    """Response from POST /api/ai/chart-context."""
    snapshot_id: Optional[str] = None
    context: ChartContextDTO
    enriched: bool = False
    backend_context_version: str = "1.0.0"
