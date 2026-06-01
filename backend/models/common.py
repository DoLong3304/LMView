"""
Common response models shared across backend services.

Provides reusable metadata structures for data freshness,
source attribution, and API response envelopes.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DataFreshness(BaseModel):
    """Reusable freshness metadata for AI-critical data responses."""
    source: str = "unknown"
    exchange: Optional[str] = None
    event_time: Optional[int] = None  # epoch ms
    last_updated: Optional[str] = None  # ISO 8601
    freshness_seconds: Optional[float] = None
    is_stale: bool = False
    is_fallback: bool = False
    warnings: List[str] = Field(default_factory=list)


class DataMetadata(BaseModel):
    """Extended metadata for data provenance."""
    data_type: str = "live"  # live, cached, computed, synthetic, placeholder
    source: str = "unknown"
    exchange: Optional[str] = None
    is_synthetic: bool = False
    is_true_data: bool = True
    freshness: Optional[DataFreshness] = None
    persisted: bool = False


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""
    total: int
    offset: int = 0
    limit: int = 50
    items: List[Any] = Field(default_factory=list)


class ErrorDetail(BaseModel):
    """Standard error detail."""
    code: str
    message: str
    field: Optional[str] = None
