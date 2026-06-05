"""
Pydantic models for the AI knowledge base management.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class KnowledgeSourceMeta(BaseModel):
    """Knowledge base source metadata."""
    id: Optional[str] = None
    source_id: str
    title: str
    description: Optional[str] = None
    domain: str = "general"
    language: str = "en"
    source_type: str = "internal_doc"
    credibility_level: str = "verified"
    review_status: str = "approved"
    allowed_for_rag: bool = True
    version: str = "1.0.0"
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class KnowledgeDocumentMeta(BaseModel):
    """Knowledge base document metadata."""
    id: Optional[str] = None
    source_id: Optional[str] = None
    title: str
    source_type: str = "internal_doc"
    domain: str = "general"
    language: Optional[str] = "en"
    content_hash: str = ""
    file_path: Optional[str] = None
    chunk_count: int = 0
    tags: List[str] = Field(default_factory=list)
    status: str = "active"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class KnowledgeIngestRequest(BaseModel):
    """Request to ingest knowledge documents."""
    source_dir: Optional[str] = None
    file_paths: Optional[List[str]] = None
    source_id: Optional[str] = None
    force_reindex: bool = False


class KnowledgeSearchRequest(BaseModel):
    """Request to search the knowledge base."""
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=6, ge=1, le=50)
    min_score: float = Field(default=0.25, ge=0.0, le=1.0)
    language: Optional[str] = None
    domain: Optional[str] = None
    tags: Optional[List[str]] = None


class KnowledgeSearchResponse(BaseModel):
    """Response from knowledge base search."""
    results: List[Dict[str, Any]] = Field(default_factory=list)
    query: str
    total_results: int = 0
    search_latency_ms: Optional[int] = None


class KnowledgeHealthResponse(BaseModel):
    """Health status of the knowledge base."""
    pgvector_available: bool = False
    source_count: int = 0
    document_count: int = 0
    chunk_count: int = 0
    embedding_count: int = 0
    embedding_model: Optional[str] = None
    status: str = "unavailable"
