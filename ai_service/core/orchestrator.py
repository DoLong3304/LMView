"""Shared Ask/Interact orchestration for LMView AI.

LangGraph DAG is the only orchestration path (legacy linear pipeline removed in v0.26.0).
"""
from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import HTTPException, status

from backend.models.ai.chat import AIChatMode, AIChatRequest, AIChatResponse
from ai_service.config import load_settings
from ai_service.context.context_service import assemble_data_caveats
from ai_service.persistence import chat_store
from ai_service.core.cache import make_cache_key, get_from_cache, set_in_cache
from ai_service.safety.knowledge_boundary import check_knowledge_boundary
from ai_service.safety.output_guard import guard_output
from ai_service.agents.state import initial_state
from ai_service.agents.graph import run_graph, scope_gate_node, expert_execution_node
from ai_service.agents.intent_router import classify_intent
from ai_service.agents.synthesis import synthesize_response_stream

logger = logging.getLogger("ai_service.core.orchestrator")

def _detect_language(text: str, request_language: Optional[str] = None) -> str:
    """Detect language from message text if not explicitly provided.

    Uses lightweight character/glyph heuristics — no external deps.
    Returns "vi" for Vietnamese, "en" for English, or request_language
    if it was explicitly set.
    """
    if request_language:
        return request_language

    if not text or not text.strip():
        return "en"

    # Vietnamese-specific characters
    vi_chars = set(
        "àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũ"
        "ưừứựửữỳýỵỷỹđÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖ"
        "ƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ"
    )

    # Count Vietnamese characters
    vi_count = sum(1 for c in text if c in vi_chars)
    total_chars = len(text.strip())

    # If significant Vietnamese character presence, classify as Vietnamese
    if total_chars > 0 and (vi_count / total_chars) > 0.02:
        return "vi"

    return "en"


def _title_from_message(message: str) -> str:
    trimmed = " ".join(message.strip().split())
    if not trimmed:
        return "LMView AI session"
    return trimmed if len(trimmed) <= 64 else f"{trimmed[:61]}..."

# ── Response section parser ───────────────────────────────────────────────────
# Phase B: Parse LLM markdown into structured sections for expandable rendering.


def _parse_response_sections(content: str) -> List[Dict[str, str]]:
    """Split markdown content into sections by `##` headings.

    Returns list of {"title": str, "content": str} dicts.
    The preamble (text before first `##`) is stored as section "" (intro).
    """
    sections: List[Dict[str, str]] = []
    # Split on `## ` headings (not `### ` subheadings)
    parts = re.split(r'(?m)^## +(.+)$', content)
    # parts[0] = preamble (before first ##)
    # parts[1] = first heading title
    # parts[2] = first heading body
    # parts[3] = second heading title  ... etc
    if not parts:
        return sections
    preamble = parts[0].strip()
    if preamble:
        sections.append({"title": "", "content": preamble})
    for i in range(1, len(parts), 2):
        title = parts[i].strip() if i < len(parts) else ""
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if title:
            sections.append({"title": title, "content": body})
    return sections


# ── Phase C: Session Memory & Compaction ──────────────────────────────────────────

def _extract_key_findings(
    content: str,
    final_state: Dict[str, Any],
) -> Dict[str, Any]:
    """Extract key findings from an assistant response for session memory.

    Returns dict with summary, findings list, and structured metadata.
    """
    findings: Dict[str, Any] = {
        "summary": "",
        "key_points": [],
        "indicators_used": [],
        "symbol": final_state.get("symbol"),
        "timeframe": final_state.get("timeframe"),
        "intent": final_state.get("intent"),
    }

    if not content:
        return findings

    # Take first 200 chars as summary
    first_para = content.split("\n\n")[0] if "\n\n" in content else content
    findings["summary"] = first_para[:200]

    # Extract key sentences (starting with ** or ### or containing numbers)
    lines = content.split("\n")
    for line in lines:
        stripped = line.strip()
        # Bold key points
        if stripped.startswith("- **") or stripped.startswith("* **"):
            findings["key_points"].append(stripped)
        elif stripped.startswith("**") and "**" in stripped[2:]:
            findings["key_points"].append(stripped)
        # Dollar prices
        elif "$" in stripped and any(c.isdigit() for c in stripped):
            if len(stripped) > 10 and len(stripped) < 200:
                findings["key_points"].append(stripped)

    # Extract indicator names from content
    indicator_names = [
        "rsi", "macd", "sma", "ema", "bollinger", "vwap", "atr",
        "stochastic", "mfi", "ichimoku", "supertrend", "psar",
    ]
    for name in indicator_names:
        if name in content.lower():
            findings["indicators_used"].append(name)

    # Keep max 5 key points
    findings["key_points"] = findings["key_points"][:5]

    return findings


async def _store_session_memory(
    session_id: str,
    user_id: str,
    user_query: str,
    assistant_content: str,
    final_state: Dict[str, Any],
    warnings: List[str],
) -> None:
    """Extract and store session memory after each assistant response."""
    from ai_service.persistence import chat_store

    # Load existing memory
    existing = await chat_store.get_session_metadata(session_id, user_id) or {}
    memory = existing.get("session_memory", {})

    if not memory:
        memory = {
            "turn_count": 0,
            "findings": [],
            "last_symbol": None,
            "last_timeframe": None,
            "compacted": False,
        }

    memory["turn_count"] = memory.get("turn_count", 0) + 1

    # Extract findings from this turn
    turn_findings = _extract_key_findings(assistant_content, final_state)
    if turn_findings.get("key_points"):
        memory["findings"].extend(turn_findings["key_points"])

    symbol = final_state.get("symbol")
    if symbol:
        memory["last_symbol"] = symbol
    timeframe = final_state.get("timeframe")
    if timeframe:
        memory["last_timeframe"] = timeframe

    # Keep only last 10 findings
    memory["findings"] = memory["findings"][-10:]

    # Check if compaction is needed (>10 turns)
    if memory["turn_count"] >= 10 and not memory.get("compacted"):
        memory["compacted"] = True
        memory["old_messages_summary"] = f"Session has {memory['turn_count']} prior exchanges. Key context preserved in findings above."

    await chat_store.update_session_metadata(
        session_id=session_id,
        user_id=user_id,
        metadata={"session_memory": memory},
    )


# ── Phase E: Walkthrough parsing ────────────────────────────────────────────────
# The LLM embeds a `<walkthrough>` JSON block at the end of its Interact mode
# response. Parse it into a TourPlan for step-by-step frontend execution.


def _parse_walkthrough_from_content(content: str) -> Optional[Dict[str, Any]]:
    """Extract and parse a `<walkthrough>` JSON block from LLM output.

    Returns a TourPlan-compatible dict, or None if no valid walkthrough found.
    """
    import json

    if not content or "<walkthrough>" not in content:
        return None

    # Extract content between <walkthrough> tags
    start_tag = "<walkthrough>"
    end_tag = "</walkthrough>"
    start_idx = content.find(start_tag)
    end_idx = content.find(end_tag, start_idx)

    if start_idx == -1 or end_idx == -1:
        return None

    raw = content[start_idx + len(start_tag):end_idx].strip()
    # Remove ``` markers if present
    if raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()

    if not raw:
        return None

    # Try to parse JSON
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Try to find the JSON object within the block
        import re
        brace_match = re.search(r'\{[\s\S]*\}', raw)
        if brace_match:
            try:
                data = json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                return None
        else:
            return None

    if not isinstance(data, dict) or "steps" not in data:
        return None

    # Validate and convert to TourPlan-compatible structure
    from backend.models.ai.tour import TourPlan
    try:
        plan = TourPlan(
            tour_id=data.get("tour_id", f"walkthrough_{int(__import__('time').time())}"),
            title=data.get("title", "Guided Analysis"),
            steps=data["steps"],
            summary=data.get("summary", ""),
        )
        return plan.model_dump(mode="json")
    except Exception as exc:
        logger.warning("Walkthrough parse validation failed: %s", exc)
        return None


def _strip_walkthrough_block(content: str) -> str:
    """Remove the `<walkthrough>` block from final content shown to user."""
    if "<walkthrough>" not in content:
        return content
    start_tag = "<walkthrough>"
    end_tag = "</walkthrough>"
    start_idx = content.find(start_tag)
    end_idx = content.find(end_tag, start_idx)
    if start_idx != -1 and end_idx != -1:
        before = content[:start_idx].rstrip()
        after = content[end_idx + len(end_tag):].lstrip()
        # Join, removing any extra blank lines
        result = before + "\n\n" + after if before and after else (before or after)
        return result.strip()
    return content


async def _acquire_session_lock(session_id: str, timeout_seconds: int = 15) -> bool:
    """Acquire a lightweight distributed lock for a session to prevent concurrent executions."""
    try:
        from backend.core.database import get_redis
        r = await get_redis()
        lock_key = f"lock:ai:session:{session_id}"
        # Set NX PX: Set if not exists, with a 15-second expiration
        ok = await r.set(lock_key, "1", ex=timeout_seconds, nx=True)
        return bool(ok)
    except Exception as exc:
        logger.warning("Failed to acquire session lock in Redis: %s", exc)
        # Fallback to True if Redis connection fails, to prevent locking out the user
        return True


async def _release_session_lock(session_id: str):
    """Release the session lock."""
    try:
        from backend.core.database import get_redis
        r = await get_redis()
        lock_key = f"lock:ai:session:{session_id}"
        await r.delete(lock_key)
    except Exception as exc:
        logger.warning("Failed to release session lock: %s", exc)


async def run_chat(body: AIChatRequest, user_id: str) -> AIChatResponse:
    """Run the unified AI pipeline for Ask or Interact mode.

    Dispatches to LangGraph DAG with a session concurrency lock.
    """
    session_id = await _ensure_session(body=body, user_id=user_id)
    if not await _acquire_session_lock(session_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another query is currently processing in this session. Please wait for it to complete."
        )
    try:
        return await run_chat_langgraph(body, user_id, session_id)
    finally:
        await _release_session_lock(session_id)


async def run_chat_langgraph(body: AIChatRequest, user_id: str, session_id: str) -> AIChatResponse:
    """Run the LangGraph multi-agent DAG pipeline."""
    start_ms = time.monotonic_ns() // 1_000_000

    # Detect language from message if not provided
    detected_language = _detect_language(body.message, body.language)
    if detected_language != body.language:
        logger.debug("Language detected: %s (request had: %s)", detected_language, body.language)
    await chat_store.store_message(
        session_id=session_id,
        user_id=user_id,
        role="user",
        content=body.message,
        metadata={
            "language": detected_language,
            "mode": body.mode.value,
            "orchestration": "langgraph",
            # Persist the chart context alongside the user message so
            # that on reload we can rebuild the exact state the LLM saw
            # (symbol, timeframe, indicators, recent candles, latest
            # candle). Without this the conversation history returned by
            # GET /sessions/{id}/messages loses the chart snapshot the
            # user was looking at when they asked.
            "chart_context": body.chart_context,
        },
    )

    # Load conversation history
    history = await _load_history(session_id=session_id, user_id=user_id)

    # Check cache for common queries
    cache_key = make_cache_key(
        message=body.message,
        symbol=body.chart_context.get("symbol") if body.chart_context else None,
        timeframe=body.chart_context.get("timeframe") if body.chart_context else None,
        indicators=body.chart_context.get("selected_indicators") if body.chart_context else None,
        language=detected_language,
        mode=body.mode.value,
    )
    cached = get_from_cache(cache_key, body.message)
    if cached is not None:
        logger.info("Cache hit for query: %s", body.message[:60])
        return AIChatResponse(**cached)

    # Check knowledge boundary before graph execution
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
    graph_state = initial_state(
        user_query=body.message,
        session_id=session_id,
        user_id=user_id,
        mode=body.mode.value,
        language=detected_language,
        chart_context=body.chart_context,
        chat_history=history,
        rag_enabled=body.rag_enabled,
        selected_model=body.model_name or None,
        selected_tier=body.model_tier or None,
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
    context_needs = final_state.get("context_needs")

    # ── Run output guard ────────────────────────────────────────────────
    # Sanitize LLM output: add disclaimer (server-side, not in LLM tokens),
    # block unsafe financial claims, remove code execution patterns.
    guarded = guard_output(
        final_content,
        language=detected_language,
    )
    final_content = guarded["content"]
    warnings.extend(guarded["warnings"])

    # Parse response into structured sections for expandable rendering
    response_sections = _parse_response_sections(final_content)

    # Extract full KB chunk data for expandable knowledge cards
    knowledge_chunks = final_state.get("rag_chunks", [])

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

    # ── Phase E: Parse walkthrough from LLM output ─────────────────────
    # The LLM may produce a `<walkthrough>` JSON block at the end of its
    # response. Parse it and use as the interactive tour plan.
    walkthrough_plan = _parse_walkthrough_from_content(final_content)

    # Plan tour for Interact mode. Prefer deterministic planner for known
    # LMView/action intents; fallback to LLM <walkthrough> only when no
    # deterministic tour applies. This prevents generic phrases like "demo"
    # from becoming stochastic technical-analysis tours.
    deterministic_tour_plan = await _plan_interact_tour(
        body=body,
        final_state=final_state,
        executed_content=final_content,
        expert_outputs=final_state.get("expert_outputs", {}),
    )
    raw_tour_plan = deterministic_tour_plan or walkthrough_plan
    if isinstance(raw_tour_plan, dict):
        from backend.models.ai.tour import TourPlan
        try:
            tour_plan = TourPlan.model_validate(raw_tour_plan)
        except Exception:
            tour_plan = None
    else:
        tour_plan = raw_tour_plan

    # Strip the walkthrough block from final content shown to user
    if walkthrough_plan:
        final_content = _strip_walkthrough_block(final_content)

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
            "context_needs": context_needs.to_dict() if context_needs else None,
            "news_context": news_context,
            "revision_count": final_state.get("revision_count", 0),
            # Persist chart actions and tool calls so they survive a page
            # reload. Without this the assistant message reappears without
            # the Interact-mode action buttons (tool_calls) or any
            # structured chart action proposals.
            "tool_calls": tool_calls,
            "chart_actions": [a.model_dump(mode="json") for a in chart_actions] if chart_actions else [],
            "rag_sources": rag_sources,
            # Phase B: persist structured sections and knowledge chunks so
            # the frontend can render expandable sections after a page reload.
            "response_sections": response_sections,
            "knowledge_chunks": knowledge_chunks,
            # Persist tour plan so Replay works after a session reload.
            # Without this the user would need to re-ask the LLM to get
            # the same visual tour.
            "tour_plan": tour_plan.model_dump(mode="json") if tour_plan else None,
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
        response_sections=response_sections,
        knowledge_chunks=knowledge_chunks,
    )

    # Store in cache (non-personalized responses only)
    if not body.session_id:
        try:
            response_dict = response.model_dump(mode="json")
            set_in_cache(cache_key, response_dict, body.message)
        except Exception as exc:
            logger.debug("Cache set failed (non-blocking): %s", exc)

    # ── Store session memory (Phase C) ─────────────────────────────────
    try:
        await _store_session_memory(
            session_id=session_id,
            user_id=user_id,
            user_query=body.message,
            assistant_content=final_content,
            final_state=final_state,
            warnings=warnings,
        )
    except Exception as exc:
        logger.warning("Session memory store failed (non-blocking): %s", exc)

    return response

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
    """Load conversation history with session memory injection (Phase C).

    Returns up to 10 recent messages. If session has memory, injects a
    "system" message with prior findings at the beginning to prevent
    context decay over long conversations.
    """
    try:
        rows = await chat_store.get_session_messages(session_id=session_id, user_id=user_id, limit=10)
        if not rows:
            return []
        history = [
            {"role": row["role"], "content": row["content"]}
            for row in rows[:-1]
            if row.get("role") in {"user", "assistant"}
        ]

        # Inject session memory for long conversations (Phase C)
        try:
            metadata = await chat_store.get_session_metadata(session_id, user_id) or {}
            memory = metadata.get("session_memory", {})
            findings = memory.get("findings", [])
            if findings and len(history) >= 6:
                memory_block = "## Prior Context\n" + "\n".join(f"- {f}" for f in findings)
                if memory.get("compacted"):
                    memory_block += f"\n\n*This session has {memory.get('turn_count', 0)} prior exchanges. Older messages compacted — key points preserved above.*"
                history.insert(0, {"role": "system", "content": memory_block})
        except Exception:
            pass

        return history
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
    """Streaming chat wrapper with session concurrency lock."""
    session_id = await _ensure_session(body=body, user_id=user_id)
    if not await _acquire_session_lock(session_id):
        result = {
            "event": "done",
            "content": "Another query is currently processing in this session. Please wait for it to complete.",
            "warnings": ["Session lock acquisition failed due to concurrent requests."],
            "done": True,
        }
        yield json.dumps(result)
        return

    try:
        async for event in _run_chat_stream_impl(body, user_id, session_id):
            yield event
    finally:
        await _release_session_lock(session_id)


async def _run_chat_stream_impl(
    body: AIChatRequest,
    user_id: str,
    session_id: str,
) -> AsyncGenerator[str, None]:
    """Streaming chat implementation. Yields SSE token events."""
    # Detect language from message if not provided
    detected_language = _detect_language(body.message, body.language)
    await chat_store.store_message(
        session_id=session_id,
        user_id=user_id,
        role="user",
        content=body.message,
        metadata={
            "language": detected_language,
            "mode": body.mode.value,
            "orchestration": "langgraph_stream",
            # Persist the chart context so the LLM can reconstruct the
            # user's view on subsequent reloads of this session.
            "chart_context": body.chart_context,
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
        language=detected_language,
        chart_context=body.chart_context,
        chat_history=history,
        selected_model=body.model_name or None,
        selected_tier=body.model_tier or None,
    )

    # Check knowledge boundary
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

    intent_state = await classify_intent(graph_state)
    graph_state["intent"] = intent_state.get("intent")
    graph_state["activated_experts"] = intent_state.get("activated_experts", [])
    graph_state["context_needs"] = intent_state.get("context_needs")

    expert_state = await expert_execution_node(graph_state)
    for k, v in expert_state.items():
        graph_state[k] = v

    # Run streaming synthesis
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
