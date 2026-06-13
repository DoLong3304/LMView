"""
Knowledge service — manages the RAG knowledge base.

Handles document ingestion, embedding generation, and knowledge base health.
Uses PostgreSQL + pgvector for vector storage and similarity search.
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.core.config import AI_EMBEDDING_MODEL, AI_KB_APPROVED_ONLY
from backend.core.postgres import get_pg_pool
from backend.models.ai.knowledge import (
    KnowledgeDocumentMeta,
    KnowledgeHealthResponse,
    KnowledgeSourceMeta,
)
from ai_service.rag.registry import allowed_for_ingestion, entry_for_file
from backend.services.ai import metrics as ai_metrics

logger = logging.getLogger("ai_service.rag.knowledge_service")

# Embedding model singleton (lazy loaded)
_embedding_model = None
_embedding_model_name: Optional[str] = None


def _get_embedding_model():
    """Lazy-load the sentence-transformers embedding model."""
    global _embedding_model, _embedding_model_name
    if _embedding_model is not None:
        return _embedding_model

    model_name = AI_EMBEDDING_MODEL
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
        _embedding_model = SentenceTransformer(model_name)
        _embedding_model_name = model_name
        logger.info("Loaded embedding model: %s", model_name)
        return _embedding_model
    except ImportError:
        logger.warning(
            "sentence-transformers not installed — RAG embeddings unavailable. "
            "Install with: pip install sentence-transformers"
        )
        return None
    except Exception as exc:
        logger.error("Failed to load embedding model %s: %s", model_name, exc)
        return None


def compute_embedding(text: str) -> Optional[List[float]]:
    """Compute embedding vector for a text string."""
    model = _get_embedding_model()
    if model is None:
        ai_metrics.record_embedding(model="unavailable", duration_sec=0.0, success=False)
        return None
    start = time.monotonic()
    try:
        embedding = model.encode(text, normalize_embeddings=True)
        duration = time.monotonic() - start
        ai_metrics.record_embedding(
            model=AI_EMBEDDING_MODEL,
            duration_sec=duration,
            success=True,
        )
        return embedding.tolist()
    except Exception as exc:
        duration = time.monotonic() - start
        ai_metrics.record_embedding(
            model=AI_EMBEDDING_MODEL,
            duration_sec=duration,
            success=False,
        )
        logger.error("Embedding computation failed: %s", exc)
        return None


def compute_content_hash(content: str) -> str:
    """Compute SHA-256 hash of content for deduplication."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# ── Chunking ──────────────────────────────────────────────────────────────────

def chunk_markdown(
    text: str,
    max_chunk_chars: int = 1200,
    overlap_chars: int = 200,
) -> List[Dict[str, Any]]:
    """
    Split markdown text into semantic chunks.

    Strategy:
    1. Split by headings (## or ###) first.
    2. If a section is too long, split by paragraphs.
    3. If a paragraph is still too long, split by sentences with overlap.

    Returns list of dicts: {text, heading, chunk_index}
    """
    chunks: List[Dict[str, Any]] = []

    # Split by headings
    heading_pattern = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)
    sections = _split_by_headings(text, heading_pattern)

    chunk_index = 0
    for heading, section_text in sections:
        section_text = section_text.strip()
        if not section_text:
            continue

        if len(section_text) <= max_chunk_chars:
            chunks.append({
                "text": section_text,
                "heading": heading,
                "chunk_index": chunk_index,
            })
            chunk_index += 1
        else:
            # Split long sections into paragraphs
            paragraphs = re.split(r"\n\n+", section_text)
            current_chunk = ""

            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue

                if len(current_chunk) + len(para) + 2 <= max_chunk_chars:
                    current_chunk = f"{current_chunk}\n\n{para}" if current_chunk else para
                else:
                    if current_chunk:
                        chunks.append({
                            "text": current_chunk,
                            "heading": heading,
                            "chunk_index": chunk_index,
                        })
                        chunk_index += 1

                    if len(para) <= max_chunk_chars:
                        current_chunk = para
                    else:
                        # Split very long paragraphs by sentences
                        sentence_chunks = _split_by_sentences(
                            para, max_chunk_chars, overlap_chars
                        )
                        for sc in sentence_chunks:
                            chunks.append({
                                "text": sc,
                                "heading": heading,
                                "chunk_index": chunk_index,
                            })
                            chunk_index += 1
                        current_chunk = ""

            if current_chunk:
                chunks.append({
                    "text": current_chunk,
                    "heading": heading,
                    "chunk_index": chunk_index,
                })
                chunk_index += 1

    return chunks


def _split_by_headings(
    text: str,
    pattern: re.Pattern,
) -> List[tuple]:
    """Split text by heading patterns. Returns [(heading, section_text)]."""
    matches = list(pattern.finditer(text))

    if not matches:
        return [(None, text)]

    sections = []

    # Content before first heading
    pre = text[: matches[0].start()].strip()
    if pre:
        sections.append((None, pre))

    for i, match in enumerate(matches):
        heading = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section_text = text[start:end].strip()
        sections.append((heading, section_text))

    return sections


def _split_by_sentences(
    text: str,
    max_chars: int,
    overlap_chars: int,
) -> List[str]:
    """Split text by sentences with overlap."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks = []
    current = ""

    for sent in sentences:
        if len(current) + len(sent) + 1 <= max_chars:
            current = f"{current} {sent}" if current else sent
        else:
            if current:
                chunks.append(current)
            current = sent

    if current:
        chunks.append(current)

    return chunks


# ── Ingestion ─────────────────────────────────────────────────────────────────

async def ingest_markdown_file(
    file_path: str,
    source_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Ingest a single markdown file into the knowledge base.

    Steps:
    1. Read file and compute content hash.
    2. Check if document already exists with same hash (skip if unchanged).
    3. Parse frontmatter metadata if present.
    4. Chunk the content.
    5. Compute embeddings for each chunk.
    6. Store document, chunks, and embeddings in PostgreSQL.

    Returns:
        Dict with document_id, chunk_count, and status.
    """
    pool = await get_pg_pool()
    if pool is None:
        return {"status": "error", "error": "Database unavailable"}

    path = Path(file_path)
    if not path.exists() or not path.is_file():
        return {"status": "error", "error": f"File not found: {file_path}"}
    registry_entry = entry_for_file(path)
    if AI_KB_APPROVED_ONLY and not allowed_for_ingestion(path):
        return {
            "status": "skipped",
            "reason": "Document is not approved for production RAG ingestion",
            "file": str(path),
        }

    content = path.read_text(encoding="utf-8")
    content_hash = compute_content_hash(content)
    title = path.stem.replace("_", " ").replace("-", " ").title()
    meta = metadata or {}
    if registry_entry:
        meta.update({
            "source_id": registry_entry.get("source_id"),
            "source_type": registry_entry.get("source_type"),
            "language": registry_entry.get("language"),
            "domain": registry_entry.get("domain"),
            "tags": registry_entry.get("tags") or [],
            "review_status": registry_entry.get("review_status"),
            "allowed_for_rag": registry_entry.get("allowed_for_rag"),
            "reviewer": registry_entry.get("reviewer"),
            "reviewed_date": registry_entry.get("reviewed_date"),
            "lmview_version_scope": registry_entry.get("lmview_version_scope"),
            "source_urls": registry_entry.get("source_urls") or [],
        })
        source_id = source_id or registry_entry.get("source_id")

    # Check for existing document with same hash
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT id FROM ai_knowledge_documents WHERE content_hash = $1 AND status = 'active'",
            content_hash,
        )
        if existing:
            return {
                "status": "unchanged",
                "document_id": str(existing["id"]),
                "message": "Document unchanged — skipping",
            }

    # Parse frontmatter if present
    frontmatter, body = _parse_frontmatter(content)
    if frontmatter:
        meta.update(frontmatter)
        title = frontmatter.get("title", title)

    # Chunk the content
    chunks = chunk_markdown(body)
    if not chunks:
        return {"status": "error", "error": "No chunks generated from content"}

    # Compute embeddings
    embeddings = []
    for chunk in chunks:
        emb = compute_embedding(chunk["text"])
        embeddings.append(emb)

    now = datetime.now(timezone.utc)
    source_uuid = None
    if source_id:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id FROM ai_knowledge_sources WHERE source_id = $1",
                source_id,
            )
            if row:
                source_uuid = row["id"]
            elif registry_entry:
                source_uuid = await conn.fetchval(
                    """
                    INSERT INTO ai_knowledge_sources (
                        source_id, title, description, domain, language,
                        source_type, credibility_level, review_status,
                        allowed_for_rag, version, tags, metadata, created_at, updated_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb, $12::jsonb, $13, $13)
                    ON CONFLICT (source_id) DO UPDATE SET
                        title = EXCLUDED.title,
                        description = EXCLUDED.description,
                        domain = EXCLUDED.domain,
                        language = EXCLUDED.language,
                        source_type = EXCLUDED.source_type,
                        credibility_level = EXCLUDED.credibility_level,
                        review_status = EXCLUDED.review_status,
                        allowed_for_rag = EXCLUDED.allowed_for_rag,
                        version = EXCLUDED.version,
                        tags = EXCLUDED.tags,
                        metadata = EXCLUDED.metadata,
                        updated_at = EXCLUDED.updated_at
                    RETURNING id
                    """,
                    source_id,
                    registry_entry.get("title") or title,
                    registry_entry.get("description"),
                    registry_entry.get("domain") or "general",
                    registry_entry.get("language") or "en",
                    registry_entry.get("source_type") or "internal_doc",
                    registry_entry.get("credibility_level") or "draft",
                    registry_entry.get("review_status") or "pending",
                    bool(registry_entry.get("allowed_for_rag")),
                    registry_entry.get("lmview_version_scope") or "1.0.0",
                    json.dumps(registry_entry.get("tags") or []),
                    json.dumps({
                        "reviewer": registry_entry.get("reviewer"),
                        "reviewed_date": registry_entry.get("reviewed_date"),
                        "source_urls": registry_entry.get("source_urls") or [],
                        "file_path": registry_entry.get("file_path"),
                    }),
                    now,
                )

    async with pool.acquire() as conn:
        async with conn.transaction():
            # Deactivate old versions of same file
            await conn.execute(
                """
                UPDATE ai_knowledge_documents SET status = 'archived', updated_at = $1
                WHERE file_path = $2 AND status = 'active'
                """,
                now, str(file_path),
            )

            # Insert document
            doc_id = await conn.fetchval(
                """
                INSERT INTO ai_knowledge_documents (
                    source_id, source_type, title, content_hash, language,
                    domain, file_path, file_size_bytes, chunk_count,
                    tags, status, created_at, updated_at, uri, metadata
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb, 'active', $11, $11, $12, $13::jsonb)
                RETURNING id
                """,
                source_uuid,
                meta.get("source_type", "internal_doc"),
                title,
                content_hash,
                meta.get("language", "en"),
                meta.get("domain", "general"),
                str(file_path),
                len(content.encode("utf-8")),
                len(chunks),
                json.dumps(meta.get("tags", [])),
                now,
                str(file_path),
                json.dumps({
                    "review_status": meta.get("review_status"),
                    "allowed_for_rag": meta.get("allowed_for_rag"),
                    "reviewer": meta.get("reviewer"),
                    "reviewed_date": meta.get("reviewed_date"),
                    "lmview_version_scope": meta.get("lmview_version_scope"),
                    "source_urls": meta.get("source_urls", []),
                }),
            )

            # Insert chunks and embeddings
            for i, chunk in enumerate(chunks):
                chunk_hash = compute_content_hash(chunk["text"])
                chunk_id = await conn.fetchval(
                    """
                    INSERT INTO ai_knowledge_chunks (
                        document_id, source_id, chunk_index, content, content_hash,
                        heading, language, char_count, created_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    RETURNING id
                    """,
                    doc_id, source_uuid, i,
                    chunk["text"], chunk_hash,
                    chunk.get("heading"),
                    meta.get("language", "en"),
                    len(chunk["text"]),
                    now,
                )

                # Insert embedding if available
                emb = embeddings[i]
                if emb is not None:
                    await conn.execute(
                        """
                        INSERT INTO ai_knowledge_embeddings (
                            chunk_id, document_id, embedding, model_name, created_at
                        )
                        VALUES ($1, $2, $3::vector, $4, $5)
                        """,
                        chunk_id, doc_id,
                        str(emb),
                        _embedding_model_name or AI_EMBEDDING_MODEL,
                        now,
                    )

    return {
        "status": "ingested",
        "document_id": str(doc_id),
        "chunk_count": len(chunks),
        "embedding_count": sum(1 for e in embeddings if e is not None),
        "title": title,
    }


async def ingest_directory(
    dir_path: str,
    source_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ingest all markdown files from a directory.

    Returns:
        Dict with total counts and per-file results.
    """
    path = Path(dir_path)
    if not path.is_dir():
        return {"status": "error", "error": f"Directory not found: {dir_path}"}

    files = sorted(path.glob("**/*.md"))
    results = []
    total_chunks = 0
    total_embeddings = 0

    for f in files:
        result = await ingest_markdown_file(str(f), source_id=source_id)
        if result is not None:
            results.append({"file": f.name, **result})
            if result.get("status") == "ingested":
                total_chunks += result.get("chunk_count", 0)
                total_embeddings += result.get("embedding_count", 0)
                ai_metrics.record_knowledge_ingest("success")
            elif result.get("status") == "unchanged":
                ai_metrics.record_knowledge_ingest("skipped")
            elif result.get("status") == "skipped":
                ai_metrics.record_knowledge_ingest("rejected")
            else:
                ai_metrics.record_knowledge_ingest("error")

    # Update KB inventory gauges so the rag-knowledge-base dashboard
    # sees current totals immediately after an ingest run.
    await _refresh_kb_inventory_gauges()

    return {
        "status": "completed",
        "files_processed": len(files),
        "files_ingested": sum(1 for r in results if r.get("status") == "ingested"),
        "files_unchanged": sum(1 for r in results if r.get("status") == "unchanged"),
        "files_skipped": sum(1 for r in results if r.get("status") == "skipped"),
        "files_errored": sum(1 for r in results if r.get("status") == "error"),
        "total_chunks": total_chunks,
        "total_embeddings": total_embeddings,
        "results": results,
    }


async def knowledge_health() -> KnowledgeHealthResponse:
    """Check knowledge base health and stats."""
    pool = await get_pg_pool()
    if pool is None:
        return KnowledgeHealthResponse(status="database_unavailable")

    try:
        async with pool.acquire() as conn:
            # Check pgvector
            pgvector_available = False
            try:
                await conn.fetchval("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
                pgvector_available = True
            except Exception:
                pass

            source_count = await conn.fetchval(
                "SELECT COUNT(*) FROM ai_knowledge_sources"
            ) or 0
            doc_count = await conn.fetchval(
                "SELECT COUNT(*) FROM ai_knowledge_documents WHERE status = 'active'"
            ) or 0
            chunk_count = await conn.fetchval(
                "SELECT COUNT(*) FROM ai_knowledge_chunks"
            ) or 0
            embedding_count = await conn.fetchval(
                "SELECT COUNT(*) FROM ai_knowledge_embeddings"
            ) or 0

        status = "healthy" if pgvector_available and embedding_count > 0 else "degraded"
        if not pgvector_available:
            status = "pgvector_unavailable"

        return KnowledgeHealthResponse(
            pgvector_available=pgvector_available,
            source_count=source_count,
            document_count=doc_count,
            chunk_count=chunk_count,
            embedding_count=embedding_count,
            embedding_model=_embedding_model_name or AI_EMBEDDING_MODEL,
            status=status,
        )

    except Exception as exc:
        logger.error("Knowledge health check failed: %s", exc)
        return KnowledgeHealthResponse(status=f"error: {str(exc)[:100]}")


def _parse_frontmatter(content: str) -> tuple:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    try:
        import yaml
        frontmatter = yaml.safe_load(parts[1]) or {}
        body = parts[2].strip()
        return frontmatter, body
    except Exception:
        return {}, content


async def _refresh_kb_inventory_gauges() -> None:
    """Refresh KB inventory gauges for the rag-knowledge-base dashboard.

    Called after an ingest run. The gauges surface totals that the
    dashboard renders as single-stat panels: total chunks, total size,
    oldest chunk age, last ingest timestamp. We compute these in a
    single SQL query and call :func:`ai_metrics.record_kb_inventory`.
    """
    pool = await get_pg_pool()
    if pool is None:
        return
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    COUNT(*)::bigint AS chunk_count,
                    COALESCE(SUM(LENGTH(c.content)), 0)::bigint AS total_size,
                    COALESCE(EXTRACT(EPOCH FROM MIN(c.created_at)), 0)::float8 AS oldest_ts,
                    COALESCE(EXTRACT(EPOCH FROM MAX(c.created_at)), 0)::float8 AS last_ingest_ts
                FROM ai_knowledge_chunks c
                JOIN ai_knowledge_documents d ON d.id = c.document_id
                WHERE d.status = 'active'
                """
            )
        if row is None:
            return
        embedding_model = _embedding_model_name or AI_EMBEDDING_MODEL
        # MiniLM produces 384-dim vectors, OpenAI 1536 — read the actual
        # vector dimension from the embeddings table when possible.
        dim_row = await pool.fetchrow(
            "SELECT vector_dims(embedding) AS dim FROM ai_knowledge_embeddings LIMIT 1"
        )
        embedding_dim = dim_row["dim"] if dim_row else 384
        ai_metrics.record_kb_inventory(
            total_chunks=int(row["chunk_count"] or 0),
            total_size_bytes=int(row["total_size"] or 0),
            last_ingest_ts=float(row["last_ingest_ts"] or 0.0),
            oldest_chunk_ts=float(row["oldest_ts"] or 0.0),
            embedding_model=embedding_model,
            embedding_dim=int(embedding_dim),
        )
    except Exception as exc:
        logger.warning("Failed to refresh KB inventory gauges: %s", exc)
