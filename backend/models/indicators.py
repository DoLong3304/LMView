"""
Pydantic models for indicator data contracts.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.models.common import DataFreshness


class IndicatorPoint(BaseModel):
    """Single indicator data point."""
    timestamp: int  # epoch ms
    value: float


class IndicatorSeries(BaseModel):
    """Time series of indicator values."""
    name: str
    indicator_type: str  # sma, ema, rsi, macd, etc.
    params: Dict[str, Any] = Field(default_factory=dict)
    points: List[IndicatorPoint] = Field(default_factory=list)
    source: str = "unknown"  # redis, influx, computed, unavailable
    freshness: Optional[DataFreshness] = None


class SupportedIndicator(BaseModel):
    """Description of a supported indicator."""
    name: str  # e.g. "sma", "rsi", "macd"
    display_name: str  # e.g. "Simple Moving Average"
    category: str  # trend, momentum, volatility, volume
    default_params: Dict[str, Any] = Field(default_factory=dict)
    available_sources: List[str] = Field(
        default_factory=lambda: ["redis", "computed"]
    )


class IndicatorSnapshot(BaseModel):
    """Latest indicator values for a symbol."""
    symbol: str
    exchange: str = "binance"
    indicators: Dict[str, Optional[float]] = Field(default_factory=dict)
    timestamp: Optional[int] = None  # epoch ms
    source: str = "unknown"
    freshness: Optional[DataFreshness] = None


class IndicatorRequest(BaseModel):
    """Request parameters for indicator data."""
    symbol: str
    indicators: List[str] = Field(default_factory=list)
    interval: str = "1m"
    limit: int = Field(200, ge=1, le=1000)
    exchange: str = "binance"


class IndicatorSummary(BaseModel):
    """Compact indicator summary for AI context."""
    symbol: str
    exchange: str = "binance"
    available: List[str] = Field(default_factory=list)
    latest_values: Dict[str, Optional[float]] = Field(default_factory=dict)
    signals: Dict[str, str] = Field(default_factory=dict)  # indicator -> signal
    source: str = "unknown"
    freshness: Optional[DataFreshness] = None
