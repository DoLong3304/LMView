"""
Pydantic models for RAG retrieval requests and results.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RAGChunkResult(BaseModel):
    """A single retrieved knowledge chunk with metadata."""
    chunk_id: str
    text: str
    score: float
    document_id: str
    document_title: str
    source_id: Optional[str] = None
    source_title: Optional[str] = None
    source_type: Optional[str] = None
    heading: Optional[str] = None
    language: Optional[str] = None
    domain: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    credibility_level: Optional[str] = None
    review_status: Optional[str] = None
    citation: Optional[Dict[str, Any]] = None


class RAGRetrievalWarning(BaseModel):
    """Warning about retrieval quality."""
    code: str
    message: str
    severity: str = "info"  # info, warning, error


class RAGRetrievalRequest(BaseModel):
    """Request for RAG retrieval."""
    query: str
    top_k: int = 6
    min_score: float = 0.25
    language: Optional[str] = None
    domain: Optional[str] = None
    tags: Optional[List[str]] = None
    source_type: Optional[str] = None
    credibility_level: Optional[str] = None
    review_status: str = "approved"
    # Batch 6: symbol/exchange/timeframe metadata filtering
    symbol: Optional[str] = None
    exchange: Optional[str] = None
    timeframe: Optional[str] = None
    # Batch 6: enable hybrid keyword+vector search
    use_hybrid_search: bool = False


class RAGRetrievalResponse(BaseModel):
    """Response from RAG retrieval."""
    chunks: List[RAGChunkResult] = Field(default_factory=list)
    query: str
    total_results: int = 0
    top_k_used: int = 6
    min_score_used: float = 0.25
    latency_ms: Optional[int] = None
    warnings: List[RAGRetrievalWarning] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
