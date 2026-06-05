"""
AI Chat endpoint — upgraded for Phase 1 with real LLM, RAG, and provider routing.

Preserves Phase 0 mock mode as fallback.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from backend.core.auth_dependencies import get_current_user
from backend.core.config import AI_ENABLE_RAG, AI_ENABLE_REAL_LLM, AI_MODE
from backend.models.ai.chat import AIChatRequest, AIChatResponse
from backend.models.ai.rag import RAGRetrievalRequest
from backend.services import ai_chat_service, ai_mock_service
from backend.services.ai.context_service import assemble_data_caveats
from backend.services.ai.output_guard import guard_output
from backend.services.ai.prompt_builder import build_ask_prompt, estimate_prompt_tokens
from backend.services.ai.provider_router import get_provider_router
from backend.services.scope_gate_service import check_scope

router = APIRouter()
logger = logging.getLogger("backend.api.ai.chat")


@router.post("/chat", response_model=AIChatResponse)
async def ai_chat(
    body: AIChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Send a message to the AI assistant.

    Phase 1: Routes to real LLM when configured, with RAG enrichment.
    Falls back to Phase 0 mock responses when AI_MODE=mock or providers fail.
    """
    user_id = current_user["id"]
    start_ms = time.monotonic_ns() // 1_000_000

    # ── 1. Scope gate ─────────────────────────────────────────────────────
    scope_result = check_scope(body.message)
    if not scope_result.in_scope:
        return AIChatResponse(
            session_id=body.session_id or "",
            message_id="",
            role="assistant",
            content=(
                "I can only help with cryptocurrency market analysis, "
                "technical indicators, chart interaction, and LMView platform usage. "
                f"Reason: {scope_result.reason}"
            ),
            provider="scope_gate",
            is_mock=True,
            warnings=[f"Message classified as out-of-scope: {scope_result.category.value}"],
        )

    # ── 2. Session management ─────────────────────────────────────────────
    session_id = body.session_id
    if not session_id:
        session = await ai_chat_service.create_session(
            user_id=user_id,
            mode=body.mode.value,
            symbol=body.chart_context.get("symbol") if body.chart_context else None,
            timeframe=body.chart_context.get("timeframe") if body.chart_context else None,
            exchange=body.chart_context.get("exchange", "binance") if body.chart_context else "binance",
        )
        if session:
            session_id = session["id"]
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not create AI session — database may be unavailable",
            )

    # ── 3. Store user message ─────────────────────────────────────────────
    user_msg = await ai_chat_service.store_message(
        session_id=session_id,
        user_id=user_id,
        role="user",
        content=body.message,
        metadata={"language": body.language, "scope": scope_result.model_dump()},
    )

    # ── 4. Decide: real LLM or mock ──────────────────────────────────────
    use_real_llm = AI_ENABLE_REAL_LLM and AI_MODE != "mock"

    if not use_real_llm:
        # Phase 0 mock path
        return await _mock_response(
            body=body,
            session_id=session_id,
            user_id=user_id,
            scope_result=scope_result,
        )

    # ── 5. Real LLM path ─────────────────────────────────────────────────
    try:
        return await _real_llm_response(
            body=body,
            session_id=session_id,
            user_id=user_id,
            scope_result=scope_result,
            start_ms=start_ms,
        )
    except Exception as exc:
        logger.error("Real LLM path failed, falling back to mock: %s", exc)
        return await _mock_response(
            body=body,
            session_id=session_id,
            user_id=user_id,
            scope_result=scope_result,
            extra_warnings=[f"LLM provider error — using mock fallback: {str(exc)[:100]}"],
        )


async def _real_llm_response(
    body: AIChatRequest,
    session_id: str,
    user_id: str,
    scope_result,
    start_ms: int,
) -> AIChatResponse:
    """Execute the full Ask Mode pipeline with real LLM."""

    # ── 5a. Assemble data caveats ─────────────────────────────────────────
    data_caveats = assemble_data_caveats(body.chart_context)

    # ── 5b. RAG retrieval ─────────────────────────────────────────────────
    rag_chunks = []
    sources = []
    if AI_ENABLE_RAG:
        try:
            from backend.services.ai.retrieval_service import retrieve

            retrieval_result = await retrieve(
                RAGRetrievalRequest(
                    query=body.message,
                    language=body.language,
                ),
                user_id=user_id,
                session_id=session_id,
            )
            rag_chunks = retrieval_result.chunks
            sources = [
                {
                    "chunk_id": c.chunk_id,
                    "title": c.document_title,
                    "source": c.source_title,
                    "score": c.score,
                    "heading": c.heading,
                }
                for c in rag_chunks
            ]
        except Exception as exc:
            logger.warning("RAG retrieval failed: %s", exc)

    # ── 5c. Load conversation history ─────────────────────────────────────
    history = []
    try:
        messages = await ai_chat_service.get_session_messages(
            session_id=session_id,
            user_id=user_id,
            limit=10,
        )
        if messages:
            history = [
                {"role": m["role"], "content": m["content"]}
                for m in messages[:-1]  # Exclude the just-stored user message
            ]
    except Exception:
        pass

    # ── 5d. Build prompt ──────────────────────────────────────────────────
    from backend.models.ai.providers import LLMCompletionRequest

    prompt_messages = build_ask_prompt(
        user_message=body.message,
        chart_context=body.chart_context,
        rag_chunks=rag_chunks,
        conversation_history=history,
        language=body.language,
        data_caveats=data_caveats,
    )

    llm_request = LLMCompletionRequest(
        messages=prompt_messages,
        temperature=0.3,
        max_tokens=2048,
    )

    # ── 5e. Route to provider ─────────────────────────────────────────────
    router_instance = get_provider_router()
    llm_response, routing = await router_instance.route_completion(llm_request)

    # ── 5f. Output guard ──────────────────────────────────────────────────
    guard_result = guard_output(llm_response.content, language=body.language)
    final_content = guard_result["content"]
    warnings = guard_result["warnings"]

    if routing.fallback_used:
        warnings.append(f"Provider fallback used: tried {routing.providers_tried}")
    if routing.is_mock:
        warnings.append("All real providers failed — mock response returned.")

    # ── 5g. Confidence estimation ─────────────────────────────────────────
    confidence = _estimate_confidence(
        has_chart_context=body.chart_context is not None,
        rag_chunk_count=len(rag_chunks),
        data_caveat_count=len(data_caveats),
        is_mock=routing.is_mock,
    )

    # ── 5h. Store assistant message ───────────────────────────────────────
    elapsed_ms = (time.monotonic_ns() // 1_000_000) - start_ms

    assistant_msg = await ai_chat_service.store_message(
        session_id=session_id,
        user_id=user_id,
        role="assistant",
        content=final_content,
        model_provider=routing.selected_provider,
        model_name=routing.selected_model,
        token_input=llm_response.token_input,
        token_output=llm_response.token_output,
        latency_ms=elapsed_ms,
        metadata={
            "is_mock": routing.is_mock,
            "grounded_context_used": body.chart_context is not None,
            "rag_chunks_used": len(rag_chunks),
            "data_caveats": data_caveats,
            "provider_routing": routing.model_dump(),
            "confidence": confidence,
        },
    )

    message_id = assistant_msg["id"] if assistant_msg else ""

    return AIChatResponse(
        session_id=session_id,
        message_id=message_id,
        role="assistant",
        content=final_content,
        provider=routing.selected_provider or "mock",
        model_name=routing.selected_model,
        is_mock=routing.is_mock,
        created_at=datetime.now(timezone.utc),
        warnings=warnings,
        grounded_context_used=body.chart_context is not None,
        confidence=confidence,
        sources=sources if sources else None,
        data_caveats=data_caveats if data_caveats else None,
        provider_metadata={
            "provider": routing.selected_provider,
            "model": routing.selected_model,
            "is_local": routing.is_local,
            "fallback_used": routing.fallback_used,
            "latency_ms": elapsed_ms,
        },
    )


async def _mock_response(
    body: AIChatRequest,
    session_id: str,
    user_id: str,
    scope_result,
    extra_warnings: list[str] | None = None,
) -> AIChatResponse:
    """Generate Phase 0 mock response — preserved for fallback/testing."""
    mock_result = ai_mock_service.generate_mock_response(
        message=body.message,
        mode=body.mode.value,
        chart_context=body.chart_context,
        language=body.language,
    )

    assistant_msg = await ai_chat_service.store_message(
        session_id=session_id,
        user_id=user_id,
        role="assistant",
        content=mock_result["content"],
        model_provider=mock_result["provider"],
        metadata={"is_mock": True, "grounded_context_used": mock_result["grounded_context_used"]},
    )

    message_id = assistant_msg["id"] if assistant_msg else ""

    warnings = mock_result["warnings"]
    if extra_warnings:
        warnings.extend(extra_warnings)

    return AIChatResponse(
        session_id=session_id,
        message_id=message_id,
        role="assistant",
        content=mock_result["content"],
        provider=mock_result["provider"],
        model_name=mock_result["model_name"],
        is_mock=mock_result["is_mock"],
        created_at=datetime.now(timezone.utc),
        warnings=warnings,
        suggested_actions=mock_result["suggested_actions"],
        chart_actions=mock_result["chart_actions"],
        grounded_context_used=mock_result["grounded_context_used"],
    )


def _estimate_confidence(
    has_chart_context: bool,
    rag_chunk_count: int,
    data_caveat_count: int,
    is_mock: bool,
) -> float:
    """Estimate confidence level for the response."""
    if is_mock:
        return 0.0

    confidence = 0.5

    if has_chart_context:
        confidence += 0.15
    if rag_chunk_count >= 3:
        confidence += 0.2
    elif rag_chunk_count >= 1:
        confidence += 0.1

    # Reduce confidence for data caveats
    confidence -= min(0.2, data_caveat_count * 0.05)

    return round(max(0.1, min(0.95, confidence)), 2)
