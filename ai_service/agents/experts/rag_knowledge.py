"""RAG / Knowledge Base Expert — retrieves and structures knowledge chunks.

Uses the existing pgvector-based retrieval service to find relevant
knowledge base entries for the user query.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from ai_service.agents.base_expert import BaseExpert
from ai_service.agents.state import AgentState
from ai_service.agents.types import ExpertOutput

logger = logging.getLogger("ai_service.agents.experts.rag_knowledge")


class RAGKnowledgeExpert(BaseExpert):
    """Retrieves relevant knowledge base chunks via pgvector."""

    name = "rag_knowledge"

    async def execute(self, state: AgentState) -> ExpertOutput:
        """Retrieve RAG chunks for the user query."""
        user_query = state.get("user_query", "")
        user_id = state.get("user_id", "")
        session_id = state.get("session_id", "")
        language = state.get("language")

        # ── Context needs aware: skip RAG if not needed ────────────────
        context_needs = state.get("context_needs")
        if context_needs is not None and not context_needs.needs_rag:
            logger.warning(
                "RAG skipped by context needs analysis for: %s",
                user_query[:60],
            )
            return ExpertOutput(
                expert_name=self.name,
                content="RAG retrieval skipped — simple price/technical query without KB requirement.",
                structured_data={"chunks": [], "sources": [], "total_retrieved": 0},
                confidence=0.1,
                warnings=[],
            )

        data_sources: List[str] = []
        warnings: List[str] = []
        structured: Dict[str, Any] = {
            "chunks": [],
            "sources": [],
            "total_retrieved": 0,
        }

        try:
            from ai_service.config import load_settings
            settings = load_settings()
            # Check state-level override first (ablation testing),
            # then fall back to global config.
            state_rag = state.get("rag_enabled")
            if state_rag is not None:
                rag_active = state_rag
            else:
                rag_active = settings.rag_enabled

            if not rag_active:
                return ExpertOutput(
                    expert_name=self.name,
                    content="RAG retrieval is disabled.",
                    structured_data=structured,
                    confidence=0.1,
                    warnings=["RAG is disabled in configuration."],
                )

            from backend.models.ai.rag import RAGRetrievalRequest
            from ai_service.rag.retrieval_service import retrieve

            # Extract chart context for metadata filtering
            chart_context = state.get("chart_context") or {}
            symbol = chart_context.get("symbol") or state.get("symbol")
            exchange = chart_context.get("exchange") or state.get("exchange", "binance")
            timeframe = chart_context.get("timeframe") or state.get("timeframe")

            retrieval_result = await retrieve(
                RAGRetrievalRequest(
                    query=user_query,
                    language=language,
                    review_status="approved",
                    symbol=symbol,
                    exchange=exchange,
                    timeframe=timeframe,
                    use_hybrid_search=True,
                ),
                user_id=user_id,
                session_id=session_id,
            )

            chunks = retrieval_result.chunks
            sources = [
                {
                    "chunk_id": chunk.chunk_id,
                    "title": chunk.document_title,
                    "source": chunk.source_title,
                    "score": chunk.score,
                    "heading": chunk.heading,
                }
                for chunk in chunks
            ]

            rag_warnings = [
                w.message for w in retrieval_result.warnings
                if w.severity in {"warning", "error"}
            ]

            structured["chunks"] = [
                {
                    "text": chunk.text,
                    "title": chunk.document_title,
                    "source": chunk.source_title,
                    "source_type": chunk.source_type,
                    "credibility_level": chunk.credibility_level,
                    "review_status": chunk.review_status,
                    "score": chunk.score,
                    "heading": chunk.heading,
                }
                for chunk in chunks
            ]
            structured["sources"] = sources
            structured["total_retrieved"] = len(chunks)

            if chunks:
                data_sources.append("pgvector_rag")
            warnings.extend(rag_warnings)

            # ── Retrieval-evidence confidence ─────────────────────────────
            # Grounding: RAG confidence reflects:
            #  1) Chunk count (more sources = broader evidence)
            #  2) Relevance scores (high-scoring chunks are more reliable)
            #  3) Source diversity (different docs vs same doc)
            chunk_count = len(chunks)
            avg_score = sum((c.score or 0) for c in chunks) / max(chunk_count, 1) if chunks else 0
            evidence = min(0.65, 0.15 + chunk_count * 0.07)
            relevance_bonus = min(0.2, avg_score * 0.25)
            confidence = max(0.1, min(0.88, evidence + relevance_bonus))
            content = f"Retrieved {len(chunks)} knowledge base entries."

            return ExpertOutput(
                expert_name=self.name,
                content=content,
                structured_data=structured,
                confidence=confidence,
                data_sources=data_sources,
                warnings=warnings,
            )

        except Exception as exc:
            logger.warning("RAG retrieval failed: %s", exc)
            return ExpertOutput(
                expert_name=self.name,
                content="Knowledge base retrieval failed.",
                structured_data=structured,
                confidence=0.1,
                error=str(exc)[:500],
                warnings=[f"RAG retrieval error: {str(exc)[:200]}"],
            )
