"""Shared Ask/Interact orchestration for LMView AI."""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from backend.models.ai.chat import AIChatRequest, AIChatResponse
from backend.models.ai.providers import LLMCompletionRequest, LLMMessage
from backend.models.ai.rag import RAGRetrievalRequest
from ai_service.actions.registry import propose_tool_calls, tool_calls_to_chart_actions
from ai_service.actions.validator import validate_actions
from ai_service.config import load_settings
from ai_service.context.context_service import assemble_data_caveats, assemble_news_context
from ai_service.persistence import chat_store
from ai_service.prompts.prompt_builder import build_ask_prompt
from ai_service.providers.router import get_provider_router
from ai_service.rag.retrieval_service import retrieve
from ai_service.safety.output_guard import guard_output
from ai_service.safety.scope_gate import check_scope

logger = logging.getLogger("ai_service.core.orchestrator")


TOOL_CATALOG_LEGACY = """**Chart Tool Catalog (for Interact mode proposals):**
- `add_indicator` — add technical indicator (RSI, MACD, SMA, EMA, Bollinger, VWAP, ATR, etc.)
- `remove_indicator` — remove an indicator from the chart
- `set_timeframe` — switch timeframe (1s, 1m, 5m, 15m, 1h, 4h, 1d, 1w)
- `set_chart_type` — change chart type (candles, bars, line, area, heikinAshi, renko)
- `draw_trendline` — draw a trendline between two price/time points
- `highlight_candles` — highlight a range of candles by index or timestamp
- `highlight_region` — highlight a rectangular region (price + time)
- `highlight_chart_area` — highlight by percentage coordinates
- `create_annotation` — add a text annotation at a chart point
- `draw_tool` — select or place a drawing tool (trendline, fibonacci, rectangle, cursor)
- `set_visible_range` — set visible time range on the chart
- `start_tour` — launch the interactive LMView workspace guided tour
- `highlight_section` — highlight a UI section for guided learning
"""


def _build_tool_catalog_text_legacy() -> str:
    return TOOL_CATALOG_LEGACY


def _title_from_message(message: str) -> str:
    trimmed = " ".join(message.strip().split())
    if not trimmed:
        return "LMView AI session"
    return trimmed if len(trimmed) <= 64 else f"{trimmed[:61]}..."


async def run_chat(body: AIChatRequest, user_id: str) -> AIChatResponse:
    """Run the unified AI pipeline for Ask or Interact mode.

    Dispatches to LangGraph DAG or legacy linear pipeline based on
    the ``AI_ORCHESTRATION`` environment variable.
    """
    settings = load_settings()

    if settings.orchestration_mode == "langgraph":
        return await run_chat_langgraph(body, user_id)

    return await _run_chat_legacy(body, user_id)


# ── LangGraph orchestration path ─────────────────────────────────────────────

async def run_chat_langgraph(body: AIChatRequest, user_id: str) -> AIChatResponse:
    """Run the LangGraph multi-agent DAG pipeline."""
    start_ms = time.monotonic_ns() // 1_000_000

    session_id = await _ensure_session(body=body, user_id=user_id)
    await chat_store.store_message(
        session_id=session_id,
        user_id=user_id,
        role="user",
        content=body.message,
        metadata={
            "language": body.language,
            "mode": body.mode.value,
            "orchestration": "langgraph",
        },
    )

    # Load conversation history
    history = await _load_history(session_id=session_id, user_id=user_id)

    # Build initial graph state
    from ai_service.agents.state import initial_state
    from ai_service.agents.graph import run_graph

    graph_state = initial_state(
        user_query=body.message,
        session_id=session_id,
        user_id=user_id,
        mode=body.mode.value,
        language=body.language,
        chart_context=body.chart_context,
        chat_history=history,
    )

    # Execute the graph
    final_state = await run_graph(graph_state)

    elapsed_ms = (time.monotonic_ns() // 1_000_000) - start_ms

    # Handle out-of-scope early exit
    scope_response = final_state.get("scope_response")
    if scope_response is not None:
        return AIChatResponse(
            session_id=session_id,
            message_id="",
            role="assistant",
            content=scope_response,
            provider="none",
            model_name="scope_gate",
            is_mock=False,
            warnings=[f"Message classified as out-of-scope: {final_state.get('scope_category', 'unknown')}"],
        )

    # Extract results from final state
    final_content = final_state.get("final_content", "")
    if not final_content:
        final_content = final_state.get("synthesized_response", "Analysis could not be completed.")

    warnings = list(final_state.get("warnings", []))
    token_usage = final_state.get("token_usage", {"input": 0, "output": 0})
    routing = final_state.get("provider_routing", {})
    tool_calls = final_state.get("tool_calls")
    chart_actions_raw = final_state.get("chart_actions")
    confidence = final_state.get("confidence", 0.5)
    data_caveats = final_state.get("data_caveats", [])
    news_context = final_state.get("news_context")
    rag_sources = final_state.get("rag_sources", [])
    intent = final_state.get("intent")
    activated_experts = final_state.get("activated_experts", [])

    # Parse chart actions through the existing validator
    chart_actions = []
    if chart_actions_raw:
        from backend.models.ai.chart_actions import AIChartAction
        for raw_action in chart_actions_raw:
            try:
                chart_actions.append(AIChartAction(**raw_action))
            except Exception:
                pass

    # Estimate cost
    estimated_cost_usd = _estimate_cost(
        token_usage.get("input"),
        token_usage.get("output"),
        routing.get("selected_provider"),
    )

    # Store execution trace
    from ai_service.agents.persistence import store_execution
    execution_id = await store_execution(final_state)

    # Store assistant message
    assistant_msg = await chat_store.store_message(
        session_id=session_id,
        user_id=user_id,
        role="assistant",
        content=final_content,
        model_provider=routing.get("selected_provider"),
        model_name=routing.get("selected_model"),
        token_input=token_usage.get("input"),
        token_output=token_usage.get("output"),
        latency_ms=elapsed_ms,
        metadata={
            "is_mock": False,
            "mode": body.mode.value,
            "orchestration": "langgraph",
            "agent_execution_id": execution_id,
            "intent": intent.to_dict() if intent else None,
            "activated_experts": activated_experts,
            "expert_timing": final_state.get("timing", {}),
            "confidence": confidence,
            "token_input": token_usage.get("input"),
            "token_output": token_usage.get("output"),
            "estimated_cost_usd": estimated_cost_usd,
            "data_caveats": data_caveats,
            "news_context": news_context,
            "revision_count": final_state.get("revision_count", 0),
        },
    )

    return AIChatResponse(
        session_id=session_id,
        message_id=assistant_msg["id"] if assistant_msg else "",
        role="assistant",
        content=final_content,
        provider=routing.get("selected_provider", "none"),
        model_name=routing.get("selected_model"),
        is_mock=False,
        created_at=datetime.now(timezone.utc),
        warnings=warnings,
        suggested_actions=_suggested_prompts(body),
        tool_calls=tool_calls,
        chart_actions=chart_actions or None,
        grounded_context_used=body.chart_context is not None,
        confidence=confidence,
        sources=rag_sources or None,
        data_caveats=data_caveats or None,
        provider_metadata={
            "provider_mode": routing.get("provider_mode"),
            "effective_provider": routing.get("selected_provider"),
            "model": routing.get("selected_model"),
            "is_local": routing.get("is_local", False),
            "fallback_used": routing.get("fallback_used", False),
            "latency_ms": elapsed_ms,
            "token_input": token_usage.get("input"),
            "token_output": token_usage.get("output"),
            "orchestration": "langgraph",
            "activated_experts": activated_experts,
            "agent_execution_id": execution_id,
        },
        token_input=token_usage.get("input"),
        token_output=token_usage.get("output"),
        estimated_cost_usd=estimated_cost_usd,
        news_context=news_context,
    )


# ── Legacy linear pipeline (unchanged) ───────────────────────────────────────

async def _run_chat_legacy(body: AIChatRequest, user_id: str) -> AIChatResponse:
    """Run the original linear AI pipeline (pre-LangGraph).

    This is the existing ``run_chat`` implementation, kept intact for
    backward compatibility when ``AI_ORCHESTRATION=legacy``.
    """
    start_ms = time.monotonic_ns() // 1_000_000
    settings = load_settings()
    scope_result = check_scope(body.message)

    if not scope_result.in_scope:
        return AIChatResponse(
            session_id=body.session_id or "",
            message_id="",
            role="assistant",
            content=(
                "I can only help with cryptocurrency market analysis, technical indicators, "
                "chart interaction, and LMView platform usage. "
                f"Reason: {scope_result.reason}"
            ),
            provider="none",
            model_name="scope_gate",
            is_mock=False,
            warnings=[f"Message classified as out-of-scope: {scope_result.category.value}"],
        )

    session_id = await _ensure_session(body=body, user_id=user_id)
    await chat_store.store_message(
        session_id=session_id,
        user_id=user_id,
        role="user",
        content=body.message,
        metadata={
            "language": body.language,
            "scope": scope_result.model_dump(),
            "mode": body.mode.value,
        },
    )

    data_caveats = assemble_data_caveats(body.chart_context)
    news_context = await assemble_news_context(
        chart_context=body.chart_context,
        user_query=body.message,
    )
    # Add news caveats to data caveats
    if news_context and news_context.caveats:
        data_caveats.extend(news_context.caveats)

    rag_chunks, sources, rag_warnings = await _retrieve_context(
        body=body,
        user_id=user_id,
        session_id=session_id,
        enabled=settings.rag_enabled,
    )
    history = await _load_history(session_id=session_id, user_id=user_id)
    prompt_messages = build_ask_prompt(
        user_message=body.message,
        chart_context=body.chart_context,
        rag_chunks=rag_chunks,
        conversation_history=history,
        language=body.language,
        data_caveats=data_caveats,
        news_context=news_context,
    )
    if body.mode.value == "interact":
        prompt_messages.insert(
            1,
            LLMMessage(
                role="system",
                content=(
                    "Interact mode: You may propose LMView chart actions as tool calls. "
                    "Never execute actions directly. Return prose first; backend will "
                    "normalize action proposals for user approval.\n\n"
                    "Step-by-step analysis guidance: After presenting your analysis, "
                    "propose ONE specific chart action per response that would help the user "
                    "understand the data better — e.g., adding an RSI indicator, highlighting "
                    "a support zone, switching to a 4H timeframe, or starting the guided tour. "
                    "Use the tool catalog below to select the correct action type.\n\n"
                    + _build_tool_catalog_text_legacy()
                ),
                name="interaction_policy",
            ),
        )

    llm_request = LLMCompletionRequest(
        messages=prompt_messages,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
        top_p=settings.top_p,
        metadata={"mode": body.mode.value},
    )

    provider_router = get_provider_router()
    llm_response, routing = await provider_router.route_completion(llm_request)
    guard_result = guard_output(llm_response.content, language=body.language)
    final_content = guard_result["content"]
    warnings = list(guard_result["warnings"]) + rag_warnings
    if routing.fallback_used:
        warnings.append(f"Provider fallback used: tried {routing.providers_tried}")
    if routing.selected_provider == "none":
        warnings.append("No local/API AI provider available; generic system answer returned.")

    tool_calls = propose_tool_calls(body.message, body.mode.value)
    chart_actions = tool_calls_to_chart_actions(tool_calls)
    validation = validate_actions(chart_actions) if chart_actions else {
        "valid": True,
        "errors": [],
        "warnings": [],
        "validated_actions": [],
    }
    if validation["errors"]:
        warnings.extend(validation["errors"])
        chart_actions = []

    elapsed_ms = (time.monotonic_ns() // 1_000_000) - start_ms
    confidence = _estimate_confidence(
        has_chart_context=body.chart_context is not None,
        rag_chunk_count=len(rag_chunks),
        data_caveat_count=len(data_caveats),
        provider=routing.selected_provider,
        has_news_context=news_context is not None and news_context.article_count > 0,
    )
    estimated_cost_usd = _estimate_cost(
        llm_response.token_input,
        llm_response.token_output,
        routing.selected_provider,
    )

    assistant_msg = await chat_store.store_message(
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
            "is_mock": False,
            "mode": body.mode.value,
            "grounded_context_used": body.chart_context is not None,
            "rag_chunks_used": len(rag_chunks),
            "data_caveats": data_caveats,
            "provider_routing": routing.model_dump(),
            "confidence": confidence,
            "token_input": llm_response.token_input,
            "token_output": llm_response.token_output,
            "estimated_cost_usd": estimated_cost_usd,
            "tool_calls": tool_calls,
            "chart_actions": [a.model_dump(mode="json") for a in chart_actions],
            "news_context": news_context.to_dict() if news_context else None,
        },
    )

    return AIChatResponse(
        session_id=session_id,
        message_id=assistant_msg["id"] if assistant_msg else "",
        role="assistant",
        content=final_content,
        provider=routing.selected_provider or "none",
        model_name=routing.selected_model,
        is_mock=False,
        created_at=datetime.now(timezone.utc),
        warnings=warnings,
        suggested_actions=_suggested_prompts(body),
        tool_calls=tool_calls or None,
        chart_actions=chart_actions or None,
        grounded_context_used=body.chart_context is not None,
        confidence=confidence,
        sources=sources or None,
        data_caveats=data_caveats or None,
        provider_metadata={
            "provider_mode": settings.mode,
            "effective_provider": routing.selected_provider,
            "model": routing.selected_model,
            "is_local": routing.is_local,
            "fallback_used": routing.fallback_used,
            "latency_ms": elapsed_ms,
            "token_input": llm_response.token_input,
            "token_output": llm_response.token_output,
            "usage_schema": "OpenAI-compatible prompt_tokens/completion_tokens/total_tokens",
        },
        token_input=llm_response.token_input,
        token_output=llm_response.token_output,
        estimated_cost_usd=estimated_cost_usd,
        news_context=news_context.to_dict() if news_context else None,
    )


# ── Shared helpers ────────────────────────────────────────────────────────────

async def _ensure_session(body: AIChatRequest, user_id: str) -> str:
    if body.session_id:
        return body.session_id
    session = await chat_store.create_session(
        user_id=user_id,
        mode=body.mode.value,
        title=_title_from_message(body.message),
        symbol=body.chart_context.get("symbol") if body.chart_context else None,
        timeframe=body.chart_context.get("timeframe") if body.chart_context else None,
        exchange=body.chart_context.get("exchange", "binance") if body.chart_context else "binance",
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not create AI session - database may be unavailable",
        )
    return session["id"]


async def _retrieve_context(
    body: AIChatRequest,
    user_id: str,
    session_id: str,
    enabled: bool,
) -> tuple[List[Any], List[Dict[str, Any]], List[str]]:
    if not enabled:
        return [], [], []
    try:
        retrieval_result = await retrieve(
            RAGRetrievalRequest(
                query=body.message,
                language=body.language,
                review_status="approved",
            ),
            user_id=user_id,
            session_id=session_id,
        )
        sources = [
            {
                "chunk_id": chunk.chunk_id,
                "title": chunk.document_title,
                "source": chunk.source_title,
                "score": chunk.score,
                "heading": chunk.heading,
            }
            for chunk in retrieval_result.chunks
        ]
        warnings = [w.message for w in retrieval_result.warnings if w.severity in {"warning", "error"}]
        return retrieval_result.chunks, sources, warnings
    except Exception as exc:
        logger.warning("RAG retrieval failed: %s", exc)
        return [], [], [f"RAG retrieval failed: {str(exc)[:120]}"]


async def _load_history(session_id: str, user_id: str) -> List[Dict[str, str]]:
    try:
        rows = await chat_store.get_session_messages(session_id=session_id, user_id=user_id, limit=10)
        if not rows:
            return []
        return [
            {"role": row["role"], "content": row["content"]}
            for row in rows[:-1]
            if row.get("role") in {"user", "assistant"}
        ]
    except Exception:
        return []


def _estimate_confidence(
    has_chart_context: bool,
    rag_chunk_count: int,
    data_caveat_count: int,
    provider: Optional[str],
    has_news_context: bool = False,
) -> float:
    if provider == "none":
        return 0.2
    confidence = 0.55
    if has_chart_context:
        confidence += 0.15
    if rag_chunk_count >= 3:
        confidence += 0.15
    elif rag_chunk_count >= 1:
        confidence += 0.08
    if has_news_context:
        confidence += 0.05
    confidence -= min(0.2, data_caveat_count * 0.04)
    return round(max(0.1, min(0.95, confidence)), 2)


def _estimate_cost(
    token_input: Optional[int],
    token_output: Optional[int],
    provider: Optional[str],
) -> Optional[float]:
    if token_input is None and token_output is None:
        return None
    if provider in {"local", "none"}:
        return 0.0
    input_cost = (token_input or 0) / 1_000_000 * 0.5
    output_cost = (token_output or 0) / 1_000_000 * 1.5
    return round(input_cost + output_cost, 6)


def _suggested_prompts(body: AIChatRequest) -> List[str]:
    symbol = "this market"
    timeframe = "current timeframe"
    if body.chart_context:
        symbol = body.chart_context.get("symbol") or symbol
        timeframe = body.chart_context.get("timeframe") or timeframe
    return [
        f"What is the current trend for {symbol}?",
        f"Explain momentum signals on {timeframe}.",
        "Show me a guided tour of this workspace.",
    ]

