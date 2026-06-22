"""Shared Ask/Interact orchestration for LMView AI.

LangGraph DAG is the only orchestration path (legacy linear pipeline removed in v0.26.0).
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import HTTPException, status

from backend.models.ai.chat import AIChatMode, AIChatRequest, AIChatResponse
from ai_service.config import load_settings
from ai_service.context.context_service import assemble_data_caveats
from ai_service.persistence import chat_store

logger = logging.getLogger("ai_service.core.orchestrator")

def _title_from_message(message: str) -> str:
    trimmed = " ".join(message.strip().split())
    if not trimmed:
        return "LMView AI session"
    return trimmed if len(trimmed) <= 64 else f"{trimmed[:61]}..."

async def run_chat(body: AIChatRequest, user_id: str) -> AIChatResponse:
    """Run the unified AI pipeline for Ask or Interact mode.

    Dispatches to LangGraph DAG (the only supported orchestration mode).
    """
    return await run_chat_langgraph(body, user_id)

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

    # Check knowledge boundary before graph execution
    from ai_service.safety.knowledge_boundary import check_knowledge_boundary

    kb_result = check_knowledge_boundary(body.message)
    if kb_result is not None:
        kb_content = kb_result.get("response", "I cannot answer that question.")
        kb_reason = kb_result.get("reason", "Query outside knowledge boundary.")
        logger.info("Knowledge boundary triggered: %s", kb_reason)
        return AIChatResponse(
            session_id=session_id,
            message_id="",
            role="assistant",
            content=kb_content,
            provider="knowledge_boundary",
            model_name="knowledge_boundary",
            is_mock=False,
            warnings=[kb_reason],
        )

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

    # Plan tour for Interact mode
    tour_plan = await _plan_interact_tour(
        body=body,
        final_state=final_state,
        executed_content=final_content,
        expert_outputs=final_state.get("expert_outputs", {}),
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
        tour_plan=tour_plan,
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

async def _plan_interact_tour(
    body: AIChatRequest,
    final_state: Dict[str, Any],
    executed_content: str,
    expert_outputs: Dict[str, Any],
) -> Any:
    """Plan a guided tour for Interact mode, if applicable."""
    if body.mode != AIChatMode.INTERACT:
        return None
    try:
        from ai_service.agents.experts.tour_planner import plan_tour
        return await plan_tour(
            user_query=body.message,
            expert_outputs=expert_outputs,
            synthesized_response=executed_content,
            chart_context=body.chart_context,
            mode=body.mode.value,
        )
    except Exception as exc:
        logger.warning("Tour planning failed (non-blocking): %s", exc)
        return None


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

async def run_chat_stream(
    body: AIChatRequest,
    user_id: str,
) -> AsyncGenerator[str, None]:
    """Streaming chat: yields SSE token events.

    Sets up session, runs scope gate + intent router + expert execution
    (same as batch pipeline), then switches to streaming synthesis.
    """
    session_id = await _ensure_session(body=body, user_id=user_id)
    await chat_store.store_message(
        session_id=session_id,
        user_id=user_id,
        role="user",
        content=body.message,
        metadata={
            "language": body.language,
            "mode": body.mode.value,
            "orchestration": "langgraph_stream",
        },
    )

    history = await _load_history(session_id=session_id, user_id=user_id)

    # Build initial state
    from ai_service.agents.state import initial_state
    graph_state = initial_state(
        user_query=body.message,
        session_id=session_id,
        user_id=user_id,
        mode=body.mode.value,
        language=body.language,
        chart_context=body.chart_context,
        chat_history=history,
    )

    # Check knowledge boundary
    from ai_service.safety.knowledge_boundary import check_knowledge_boundary

    kb_result = check_knowledge_boundary(body.message)
    if kb_result is not None:
        kb_content = kb_result.get("response", "I cannot answer that question.")
        kb_reason = kb_result.get("reason", "Query outside knowledge boundary.")
        result = {
            "event": "done",
            "content": kb_content,
            "warnings": [kb_reason],
            "done": True,
        }
        yield json.dumps(result)
        return

    # Run pre-synthesis nodes manually (scope gate → intent router → expert exec)
    from ai_service.agents.graph import scope_gate_node, expert_execution_node
    from ai_service.agents.intent_router import classify_intent

    state = await scope_gate_node(graph_state)
    if state.get("scope_response") is not None:
        # Out-of-scope — yield as final event
        result = {
            "event": "done",
            "content": state["scope_response"],
            "warnings": [f"Out-of-scope: {state.get('scope_category', 'unknown')}"],
            "done": True,
        }
        yield json.dumps(result)
        return

    # Merge scope results back
    for k, v in state.items():
        if k != "scope_response" or v is not None:
            graph_state[k] = v

    intent_state = classify_intent(graph_state)
    graph_state["intent"] = intent_state.get("intent")
    graph_state["activated_experts"] = intent_state.get("activated_experts", [])

    expert_state = await expert_execution_node(graph_state)
    for k, v in expert_state.items():
        graph_state[k] = v

    # Run streaming synthesis
    from ai_service.agents.synthesis import synthesize_response_stream
    async for event in synthesize_response_stream(graph_state):
        yield event

    # Store assistant message after streaming completes
    # (synthesize_response_stream yields the final done event with full content)


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
