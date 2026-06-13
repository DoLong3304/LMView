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
            if not settings.rag_enabled:
                return ExpertOutput(
                    expert_name=self.name,
                    content="RAG retrieval is disabled.",
                    structured_data=structured,
                    confidence=0.1,
                    warnings=["RAG is disabled in configuration."],
                )

            from backend.models.ai.rag import RAGRetrievalRequest
            from ai_service.rag.retrieval_service import retrieve

            retrieval_result = await retrieve(
                RAGRetrievalRequest(
                    query=user_query,
                    language=language,
                    review_status="approved",
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
                    "text": chunk.text[:800],
                    "title": chunk.document_title,
                    "source": chunk.source_title,
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

            confidence = min(0.85, 0.2 + len(chunks) * 0.1)
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
