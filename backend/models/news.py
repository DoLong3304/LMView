"""
Pydantic models for news persistence and retrieval.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.models.common import DataFreshness


class NewsArticleResponse(BaseModel):
    """News article response (aligned with frontend NewsArticle type)."""
    id: str
    source: str
    title: str
    summary: Optional[str] = None
    url: Optional[str] = None
    published_at: str  # ISO 8601
    fetched_at: Optional[str] = None
    symbols: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None
    language: Optional[str] = None


class NewsListResponse(BaseModel):
    """Response for news list endpoints with metadata."""
    total: int
    articles: List[Dict[str, Any]] = Field(default_factory=list)
    last_update: Optional[str] = None
    source: str = "memory"  # memory, postgres, mixed
    persisted: bool = False
    freshness: Optional[DataFreshness] = None


class NewsPersistenceStats(BaseModel):
    """Statistics about news persistence."""
    total_articles: int = 0
    sources: List[str] = Field(default_factory=list)
    oldest_article: Optional[str] = None
    newest_article: Optional[str] = None
    persisted: bool = False
