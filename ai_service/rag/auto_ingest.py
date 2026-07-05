"""Auto-ingestion trigger for the RAG knowledge base.

Scans ``docs/ai/knowledge_base/approved/`` for new or modified Markdown
files and ingests them into pgvector via the existing ``ingest_markdown_file``
pipeline. Designed to run as a startup task or periodic background job.

Usage:
    await ingest_all_approved()  # one-shot, e.g. on app startup
    await auto_ingest_watch()    # continuous file-watch loop
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

from backend.core.config import AI_EMBEDDING_MODEL
from backend.core.postgres import get_pg_pool
from ai_service.rag.registry import allowed_for_ingestion, entry_for_file

logger = logging.getLogger("ai_service.rag.auto_ingest")

_KNOWN_ROOT: Optional[Path] = None

def knowledge_base_root() -> Path:
    global _KNOWN_ROOT
    if _KNOWN_ROOT is None:
        # Typically under LMView/docs/ai/knowledge_base
        candidates = [
            Path("docs/ai/knowledge_base"),
            Path("/mnt/efs/LMView/docs/ai/knowledge_base"),
        ]
        for p in candidates:
            if p.is_dir():
                _KNOWN_ROOT = p
                break
        if _KNOWN_ROOT is None:
            _KNOWN_ROOT = Path("docs/ai/knowledge_base")
    return _KNOWN_ROOT


async def _already_ingested(file_hash: str) -> bool:
    """Check whether a file with given content_hash is already in the DB."""
    pool = await get_pg_pool()
    if pool is None:
        return False
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id FROM ai_knowledge_documents WHERE content_hash = $1 AND status = 'active'",
            file_hash,
        )
        return row is not None


async def ingest_all_approved() -> Dict[str, int]:
    """Scan the approved KB directory and ingest any new/modified files.

    Returns a summary dict with counts of ingested, unchanged, skipped, and errored files.
    """
    from ai_service.rag.knowledge_service import ingest_markdown_file

    root = knowledge_base_root() / "approved"
    if not root.is_dir():
        logger.warning("Approved KB directory %s does not exist", root)
        return {"ingested": 0, "unchanged": 0, "skipped": 0, "errored": 0}

    counts: Dict[str, int] = {"ingested": 0, "unchanged": 0, "skipped": 0, "errored": 0}
    for md_file in sorted(root.glob("*.md")):
        if not allowed_for_ingestion(md_file):
            logger.info("Skipping %s — not in registry or not approved", md_file.name)
            counts["skipped"] += 1
            continue

        # Check content hash
        file_hash = hashlib.sha256(md_file.read_bytes()).hexdigest()
        if await _already_ingested(file_hash):
            counts["unchanged"] += 1
            continue

        result = await ingest_markdown_file(str(md_file))
        if result and result.get("status") == "ingested":
            counts["ingested"] += 1
            logger.info("Ingested %s (%d chunks)", md_file.name, result.get("chunk_count", 0))
        elif result and result.get("status") == "unchanged":
            counts["unchanged"] += 1
        else:
            counts["errored"] += 1
            logger.error("Failed to ingest %s: %s", md_file.name, result)

    return counts


async def reindex_all_embeddings() -> Dict[str, Any]:
    """Recompute embeddings for ALL active chunks using current embedding model.

    Called after model upgrade to refresh the vector index in-place.
    Chunks retain same IDs/content — only the embedding vector changes.

    Returns stats:
        total: chunks processed
        updated: embedding rows updated
        failed: chunk count that errored
    """
    from ai_service.rag.knowledge_service import compute_embedding

    pool = await get_pg_pool()
    if pool is None:
        return {"status": "error", "error": "Database unavailable"}

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT c.id, c.content
            FROM ai_knowledge_chunks c
            JOIN ai_knowledge_documents d ON d.id = c.document_id
            WHERE d.status = 'active'
            ORDER BY c.id
            """
        )

    total = len(rows)
    updated = 0
    failed = 0
    batch_size = 50

    for batch_start in range(0, total, batch_size):
        batch = rows[batch_start:batch_start + batch_size]
        batch_embeddings = []

        for row in batch:
            chunk_id = row["id"]
            content = row["content"]
            emb = compute_embedding(content)
            if emb is None:
                failed += 1
                continue
            batch_embeddings.append((chunk_id, emb))

        if not batch_embeddings:
            continue

        try:
            async with pool.acquire() as conn:
                # Bulk upsert via unnest for speed
                chunk_ids = [str(cid) for cid, _emb in batch_embeddings]
                embedding_strs = [str(emb) for _cid, emb in batch_embeddings]
                await conn.execute(
                    """
                    INSERT INTO ai_knowledge_embeddings (chunk_id, document_id, embedding, model_name, created_at)
                    SELECT
                        c.id,
                        c.document_id,
                        u.emb::vector,
                        $1,
                        NOW()
                    FROM unnest($2::uuid[], $3::text[]) AS u(id, emb)
                    JOIN ai_knowledge_chunks c ON c.id = u.id
                    ON CONFLICT (chunk_id)
                    DO UPDATE SET embedding = EXCLUDED.embedding, model_name = $1, created_at = NOW()
                    """,
                    AI_EMBEDDING_MODEL,
                    chunk_ids,
                    embedding_strs,
                )
            updated += len(batch_embeddings)
        except Exception as exc:
            logger.error("Batch reindex failed for chunk batch %d: %s", batch_start, exc)
            failed += len(batch_embeddings)

        if batch_start % 200 == 0 and batch_start > 0:
            logger.info("Reindex progress: %d/%d (updated=%d, failed=%d)", batch_start, total, updated, failed)

    return {
        "status": "completed",
        "total": total,
        "updated": updated,
        "failed": failed,
        "model": AI_EMBEDDING_MODEL,
    }
    """Continuous loop: scan approved dir every *interval_seconds* and ingest changes."""
    logger.info("Starting auto-ingest watcher (every %ds)", interval_seconds)
    while True:
        try:
            counts = await ingest_all_approved()
            total = sum(counts.values())
            if counts.get("ingested", 0) > 0:
                logger.info("Auto-ingest cycle: %s", counts)
        except Exception as exc:
            logger.error("Auto-ingest cycle failed: %s", exc)
        await asyncio.sleep(interval_seconds)
