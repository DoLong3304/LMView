"""Strongly-typed graph state for the LangGraph multi-agent DAG.

This TypedDict is the single shared state object passed through all graph
nodes. Each node reads what it needs and writes its outputs into designated
fields. LangGraph handles state merging automatically.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, TypedDict

from ai_service.agents.types import (
    ContextNeeds,
    ExpertOutput,
    IntentClassification,
    ValidationResult,
)


class AgentState(TypedDict, total=False):
    """Shared state flowing through the LangGraph DAG.

    All fields use ``total=False`` so nodes only need to populate the
    fields they own. The graph compiler verifies key existence at
    runtime edges.
    """

    # ── Input (set once at graph entry) ───────────────────────────────────
    user_query: str
    session_id: str
    user_id: str
    mode: str                                   # "ask" | "interact"
    language: Optional[str]
    selected_model: Optional[str]               # Model override from user settings/request
    selected_tier: Optional[str]                # Tier filter ('standard'|'reserved'|'benchmark')
    user_timezone: Optional[str]                # User's local timezone (e.g. "Asia/Ho_Chi_Minh")

    # ── Context (set at entry or by context-gathering nodes) ──────────────
    chat_history: List[Dict[str, str]]
    chart_context: Optional[Dict[str, Any]]
    symbol: Optional[str]
    timeframe: Optional[str]
    exchange: str

    # ── Scope gate ────────────────────────────────────────────────────────
    scope_in_scope: bool
    scope_category: Optional[str]
    scope_reason: Optional[str]
    scope_confidence: float
    scope_response: Optional[str]               # non-None means early exit

    # ── Intent routing ────────────────────────────────────────────────────
    intent: Optional[IntentClassification]
    activated_experts: List[str]
    context_needs: Optional[ContextNeeds]  # LLM-identified data requirements

    # ── Expert outputs (keyed by ExpertName.value) ────────────────────────
    expert_outputs: Dict[str, ExpertOutput]

    # ── Data gathered by experts (structured payloads) ────────────────────
    market_data: Optional[Dict[str, Any]]
    news_context: Optional[Dict[str, Any]]       # NewsContextResult.to_dict()
    rag_chunks: List[Any]
    rag_sources: List[Dict[str, Any]]
    indicator_data: Optional[Dict[str, Any]]

    # ── Synthesis ─────────────────────────────────────────────────────────
    synthesized_response: Optional[str]

    # ── RAG override for ablation testing ─────────────────────────────────
    rag_enabled: Optional[bool]
    tool_calls: Optional[List[Dict[str, Any]]]
    chart_actions: Optional[List[Dict[str, Any]]]

    # ── Reflection / Validation ───────────────────────────────────────────
    validation_result: Optional[ValidationResult]
    revision_count: int

    # ── Final output ──────────────────────────────────────────────────────
    final_content: Optional[str]

    # ── Accumulated metadata ──────────────────────────────────────────────
    data_caveats: List[str]
    warnings: List[str]
    provider_routing: Optional[Dict[str, Any]]
    confidence: float
    token_usage: Dict[str, int]                  # {"input": N, "output": N}
    timing: Dict[str, float]                     # node_name -> elapsed_ms
    estimated_cost_usd: Optional[float]
    execution_id: Optional[str]


def _extract_symbol_and_timeframe(query: str) -> tuple[Optional[str], Optional[str]]:
    """Helper to extract symbol and timeframe from query string using heuristics."""
    query_upper = query.upper()

    # Timeframe matching (1s, 1m, 5m, 15m, 1h, 4h, 1d, 1w)
    tf_match = re.search(r"\b(1S|1M|5M|15M|1H|4H|1D|1W)\b", query_upper)
    timeframe = tf_match.group(1).lower() if tf_match else None

    # Symbol matching (e.g. BTCUSDT, SOLUSDT, ETH-USDT, BTC/USDT)
    symbol = None
    symbol_match = re.search(r"\b([A-Z]{2,5})[-_/]?(USDT|USDC|BUSD|DAI)\b", query_upper)
    if symbol_match:
        symbol = f"{symbol_match.group(1)}{symbol_match.group(2)}"
    else:
        # Fallback to single asset names
        asset_match = re.search(r"\b(BTC|ETH|SOL|XRP|ADA|DOT|DOGE|SHIB|AVAX|LINK|LTC|NEAR|UNI|APT|SUI|OP|ARB)\b", query_upper)
        if asset_match:
            symbol = f"{asset_match.group(1)}USDT"

    return symbol, timeframe


def initial_state(
    user_query: str,
    session_id: str,
    user_id: str,
    mode: str = "ask",
    language: Optional[str] = None,
    chart_context: Optional[Dict[str, Any]] = None,
    chat_history: Optional[List[Dict[str, str]]] = None,
    rag_enabled: Optional[bool] = None,
    selected_model: Optional[str] = None,
    selected_tier: Optional[str] = None,
) -> AgentState:
    """Build the initial graph state from a chat request.

    This is the entry-point factory used by the LangGraph orchestrator
    before invoking the compiled graph.
    """
    symbol = None
    timeframe = None
    exchange = "binance"
    
    if chart_context:
        symbol = chart_context.get("symbol")
        timeframe = chart_context.get("timeframe")
        exchange = chart_context.get("exchange", "binance")
    else:
        symbol, timeframe = _extract_symbol_and_timeframe(user_query)
        if symbol:
            chart_context = {
                "symbol": symbol,
                "timeframe": timeframe,
                "exchange": exchange,
            }

    return AgentState(
        user_query=user_query,
        session_id=session_id,
        user_id=user_id,
        mode=mode,
        language=language,
        chat_history=chat_history or [],
        chart_context=chart_context,
        symbol=symbol,
        timeframe=timeframe,
        exchange=exchange,
        scope_in_scope=True,
        scope_category=None,
        scope_reason=None,
        scope_confidence=0.0,
        scope_response=None,
        intent=None,
        activated_experts=[],
        expert_outputs={},
        market_data=None,
        news_context=None,
        rag_chunks=[],
        rag_sources=[],
        indicator_data=None,
        synthesized_response=None,
        tool_calls=None,
        chart_actions=None,
        validation_result=None,
        revision_count=0,
        final_content=None,
        data_caveats=[],
        warnings=[],
        provider_routing=None,
        confidence=0.5,
        token_usage={"input": 0, "output": 0},
        timing={},
        estimated_cost_usd=None,
        execution_id=None,
        rag_enabled=rag_enabled,
        selected_model=selected_model,
        selected_tier=selected_tier,
        user_timezone=chart_context.get("user_timezone") if chart_context else None,
    )
