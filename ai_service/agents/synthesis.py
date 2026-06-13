"""Response Synthesis node — merges expert outputs into a single LLM call.

This is where the single LLM call happens. All data-gathering experts have
already produced structured data; the synthesis node assembles them into
a comprehensive prompt and makes one LLM completion call for best performance.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ai_service.agents.state import AgentState
from ai_service.agents.types import ExpertOutput, Timer

logger = logging.getLogger("ai_service.agents.synthesis")


SYNTHESIS_SYSTEM_PROMPT = """You are LMView AI, a bilingual (English/Vietnamese) cryptocurrency technical analysis assistant.

You have received structured analysis data from multiple expert systems. Your job is to:
1. Synthesize all expert data into a coherent, well-structured response.
2. Prioritize the most relevant information for the user's question.
3. Maintain educational tone — never give direct buy/sell recommendations.
4. Cite data sources and acknowledge limitations.
5. Respond in the same language the user writes in.

## Response Formatting & Language Rules
1. **Full Markdown Support**: Use headers (`###`), lists (`-`), bolding (`**`), and styled tables to organize information cleanly.
2. **Highlight Key Values**: Highlight important prices, percentages, indicators, and trends with clear markdown styling (e.g. **$65,420**, **+5.23%**, **RSI: 28.5 (Oversold)**, **Bullish Crossover**).
3. **No Coding Style**: Do NOT use technical variable names, JSON keys, dictionary formats, or database strings (e.g., `sma20`, `rsi14`, `btc_dominance`, `total_market_cap`, `imbalance`) in your output.
4. **Convert Variables to Human-Readable Equivalents**: Always translate raw variable/key names into natural, human-readable equivalents in your text:
   - `sma20` -> **20-day Simple Moving Average (SMA)**
   - `sma50` -> **50-day Simple Moving Average (SMA)**
   - `ema12` -> **12-period Exponential Moving Average (EMA)**
   - `ema26` -> **26-period Exponential Moving Average (EMA)**
   - `rsi` / `rsi14` -> **Relative Strength Index (RSI)**
   - `macd` -> **MACD Line**
   - `macd_signal` -> **MACD Signal Line**
   - `macd_histogram` -> **MACD Histogram**
   - `bb_upper` / `bollinger_upper` -> **Bollinger Upper Band**
   - `bb_lower` / `bollinger_lower` -> **Bollinger Lower Band**
   - `bb_width` -> **Bollinger Band Width**
   - `btc_dominance` -> **Bitcoin Dominance**
   - `total_market_cap` -> **Total Market Capitalization**
   - `imbalance` -> **Order Book Imbalance**
   - `volume_sma20` -> **20-period Volume Moving Average**
   - `atr14` -> **Average True Range (ATR)**

## Response Structure
When relevant, organize your response into these sections:
- **Market Context** — Current price, trend, and broader context
- **Technical Signals** — What indicators show (if TA data provided)
- **Order Flow** — Bid/ask dynamics, volume (if market data provided)
- **News & Sentiment** — Recent news impact (if news data provided)
- **Knowledge** — Relevant educational context (if KB data provided)
- **Key Levels** — Support/resistance zones
- **Risk Notes** — Key risks and caveats
- **⚠️ Disclaimer** — Educational purposes only, not financial advice

Not every response needs all sections. Adapt to the question.

## Important Rules
1. NEVER give direct buy/sell recommendations or guaranteed price predictions.
2. ALWAYS acknowledge data limitations from the caveats list.
3. State confidence levels honestly.
4. If data is stale or placeholder, say so.
5. Never execute code, SQL, or shell commands.
"""


async def synthesize_response(state: AgentState) -> AgentState:
    """Merge expert outputs and make the single LLM call.

    This is the core synthesis node in the LangGraph DAG.
    """
    timer = Timer().start()
    expert_outputs = state.get("expert_outputs", {})
    user_query = state.get("user_query", "")
    language = state.get("language")
    chart_context = state.get("chart_context")
    chat_history = state.get("chat_history", [])
    data_caveats = state.get("data_caveats", [])
    mode = state.get("mode", "ask")
    warnings = list(state.get("warnings", []))

    # Build context sections from expert outputs
    context_sections = _build_context_sections(expert_outputs, chart_context, data_caveats)

    # Build the prompt messages
    from backend.models.ai.providers import LLMMessage, LLMCompletionRequest

    messages: List[LLMMessage] = []

    # System prompt
    now_utc = datetime.now(timezone.utc)
    runtime = (
        f"\n## Runtime Context\n"
        f"- Current server time (UTC): {now_utc.isoformat()}\n"
        f"- Current epoch milliseconds: {int(now_utc.timestamp() * 1000)}\n"
        f"- Chart times are live runtime data — do not reject timestamps past training cutoff.\n"
    )
    system_content = SYNTHESIS_SYSTEM_PROMPT + runtime
    if language and language.lower() in ("vi", "vietnamese"):
        system_content += "\nThe user prefers Vietnamese. Respond in Vietnamese.\n"

    messages.append(LLMMessage(role="system", content=system_content))

    # Expert data as system context
    if context_sections:
        messages.append(LLMMessage(
            role="system",
            content="## Expert Analysis Data\n" + context_sections,
            name="expert_data",
        ))

    # Interact mode policy
    if mode == "interact":
        messages.append(LLMMessage(
            role="system",
            content=(
                "Interact mode: you may propose chart actions as tool calls. "
                "Never execute actions directly. Return prose first; "
                "backend normalizes action proposals for user approval."
            ),
            name="interaction_policy",
        ))

    # Conversation history (last 10)
    for msg in chat_history[-10:]:
        messages.append(LLMMessage(
            role=msg.get("role", "user"),
            content=msg.get("content", ""),
        ))

    # User message
    messages.append(LLMMessage(role="user", content=user_query))

    # Make the single LLM call
    from ai_service.providers.router import get_provider_router
    from ai_service.config import load_settings

    settings = load_settings()
    llm_request = LLMCompletionRequest(
        messages=messages,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
        top_p=settings.top_p,
        metadata={"mode": mode, "node": "synthesis"},
    )

    provider_router = get_provider_router()
    llm_response, routing = await provider_router.route_completion(llm_request)

    # Apply output guard
    from ai_service.safety.output_guard import guard_output
    guard_result = guard_output(llm_response.content, language=language)
    final_content = guard_result["content"]
    guard_warnings = list(guard_result["warnings"])

    if routing.fallback_used:
        warnings.append(f"Provider fallback used: tried {routing.providers_tried}")
    if routing.selected_provider == "none":
        warnings.append("No local/API AI provider available; generic system answer returned.")
    warnings.extend(guard_warnings)

    # Aggregate token usage
    token_usage = dict(state.get("token_usage", {"input": 0, "output": 0}))
    token_usage["input"] += llm_response.token_input or 0
    token_usage["output"] += llm_response.token_output or 0

    # Aggregate chart actions from chart_interaction expert
    chart_actions = None
    tool_calls = None
    chart_expert = expert_outputs.get("chart_interaction")
    if chart_expert and chart_expert.structured_data.get("proposed_actions"):
        raw_actions = chart_expert.structured_data["proposed_actions"]
        chart_actions = []
        tool_calls = []
        for a in raw_actions:
            act_type = a.get("action_type") or a.get("tool")
            params = a.get("params", {})
            reason = a.get("reason") or f"AI proposed {act_type}"
            req_app = a.get("requires_approval")
            if req_app is None:
                # Default requires_approval to True unless it is highlight_section or clear_ai_annotations
                req_app = act_type not in {"highlight_section", "clear_ai_annotations"}
            
            # Normalize actions for frontend and backend validation compatibility
            if act_type == "draw_trendline":
                act_type = "draw_tool"
                params = {
                    "tool": "trendline",
                    "points": [
                        {"time": params.get("from_time"), "price": params.get("from_price")},
                        {"time": params.get("to_time"), "price": params.get("to_price")},
                    ],
                    "text": params.get("color", "")
                }
            elif act_type == "create_annotation":
                act_type = "draw_tool"
                params = {
                    "tool": "text",
                    "points": [{"time": params.get("time"), "price": params.get("price")}],
                    "text": params.get("text", "")
                }
            elif act_type == "highlight_region":
                act_type = "highlight_candles"
                params = {
                    "start_time": params.get("from_time"),
                    "end_time": params.get("to_time"),
                    "label": params.get("label", "Highlighted Region"),
                }

            chart_actions.append({
                "action_type": act_type,
                "params": params,
                "reason": reason,
                "requires_approval": req_app,
            })
            tool_calls.append({
                "name": act_type,
                "arguments": params,
                "reason": reason,
                "requires_approval": req_app,
            })

    timing = dict(state.get("timing", {}))
    timing["synthesis"] = timer.elapsed_ms()

    return {
        "synthesized_response": final_content,
        "final_content": final_content,
        "tool_calls": tool_calls,
        "chart_actions": chart_actions,
        "provider_routing": routing.model_dump(),
        "warnings": warnings,
        "token_usage": token_usage,
        "timing": timing,
    }


def _build_context_sections(
    expert_outputs: Dict[str, ExpertOutput],
    chart_context: Optional[Dict[str, Any]],
    data_caveats: List[str],
) -> str:
    """Build formatted context from all expert outputs for the LLM."""
    parts: List[str] = []

    # Technical Analysis
    ta = expert_outputs.get("technical_analysis")
    if ta and ta.content and not ta.error:
        parts.append(f"### Technical Analysis (confidence: {ta.confidence:.0%})")
        parts.append(ta.content)
        if ta.structured_data.get("signals"):
            signals = ta.structured_data["signals"]
            parts.append(f"Signals: {len(signals)} detected. Trend: {ta.structured_data.get('trend_summary', 'neutral')}")
        parts.append("")

    # Market Data
    md = expert_outputs.get("market_data")
    if md and md.content and not md.error:
        parts.append(f"### Market Data (confidence: {md.confidence:.0%})")
        parts.append(md.content)
        ticker = md.structured_data.get("ticker", {})
        if ticker.get("close"):
            parts.append(f"Price: {ticker['close']}")
        parts.append("")

    # News & Sentiment
    ns = expert_outputs.get("news_sentiment")
    if ns and ns.content and not ns.error:
        parts.append(f"### News & Sentiment (confidence: {ns.confidence:.0%})")
        parts.append(ns.content)
        if ns.structured_data.get("risk_events"):
            parts.append(f"⚠️ Risk events: {ns.structured_data['risk_events']}")
        parts.append("")

    # RAG Knowledge
    rag = expert_outputs.get("rag_knowledge")
    if rag and rag.structured_data.get("total_retrieved", 0) > 0:
        parts.append(f"### Knowledge Base ({rag.structured_data['total_retrieved']} entries)")
        chunks = rag.structured_data.get("chunks", [])
        for i, chunk in enumerate(chunks[:4], 1):
            parts.append(f"[{i}] {chunk.get('title', '?')}: {chunk.get('text', '')[:400]}")
        parts.append("")

    # Chart Interaction
    ci = expert_outputs.get("chart_interaction")
    if ci and ci.structured_data.get("proposed_actions"):
        actions = ci.structured_data["proposed_actions"]
        parts.append(f"### Proposed Chart Actions ({len(actions)})")
        for action in actions:
            parts.append(f"- {action.get('tool')}: {action.get('params', {})}")
        parts.append("")

    # General
    gen = expert_outputs.get("general")
    if gen and gen.content and not gen.error:
        parts.append(f"### General Context")
        parts.append(gen.content)
        parts.append("")

    # Data caveats
    if data_caveats:
        parts.append("### ⚠️ Data Caveats")
        for caveat in data_caveats:
            parts.append(f"- {caveat}")
        parts.append("")

    return "\n".join(parts)
