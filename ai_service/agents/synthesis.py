"""Response Synthesis node — merges expert outputs into a single LLM call.

This is where the single LLM call happens. All data-gathering experts have
already produced structured data; the synthesis node assembles them into
a comprehensive prompt and makes one LLM completion call for best performance.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
import json
from typing import Any, AsyncGenerator, Dict, List, Optional

from ai_service.agents.state import AgentState
from ai_service.agents.types import ExpertOutput, Timer

logger = logging.getLogger("ai_service.agents.synthesis")

TOOL_CATALOG_TEXT = """**Chart Tool Catalog (for Interact mode proposals):**
- `set_timeframe` — switch timeframe (1s, 1m, 5m, 15m, 1h, 4h, 1d, 1w)
- `set_chart_type` — change chart type (candles, bars, line, area, heikinAshi, renko)
- `set_symbol` — switch market symbol (e.g. BTCUSDT, ETHUSDT)
- `set_visible_range` — set visible time range on the chart
- `add_indicator` — add technical indicator (RSI, MACD, SMA, EMA, Bollinger, VWAP, ATR, etc.)
- `remove_indicator` — remove an indicator from the chart
- `toggle_indicator` — toggle indicator on/off
- `configure_indicator` — update indicator settings (period, color)
- `draw_tool` — select or place a drawing tool (trendline, fibonacci, rectangle, ellipse, channel, etc.)
- `draw_trendline` — draw a trendline between two price/time points
- `create_annotation` — add a text annotation at a chart point
- `clear_drawings` — remove all AI-placed drawings
- `delete_drawing` — delete a specific drawing by id
- `set_drawing_color` — recolor an existing drawing
- `highlight_candles` — highlight candles by index or timestamp
- `highlight_region` — highlight a rectangular region (price + time)
- `highlight_chart_area` — highlight by percentage coordinates
- `highlight_contextual_zone` — highlight an analytical zone (breakout, support_test, etc.)
- `highlight_section` — highlight a UI section for guided learning
- `zoom_chart` — zoom chart in or out
- `scroll_chart` — scroll chart horizontally
- `scroll_chart_to_time` — scroll to a specific timestamp
- `reset_chart_view` — reset to default zoom/scroll
- `open_panel` — open a right panel (watchlist, orderbook, trades, ai)
- `close_panel` — close the right panel
- `switch_panel_tab` — switch between watchlist/orderbook/trades
- `switch_app_view` — switch between charts/news/screener
- `view_section` — open and highlight a section
- `open_settings` — open settings modal
- `close_settings` — close settings modal
- `fetch_historical_prices` — fetch historical candle data
- `open_news_popup` — open a news article popup
- `navigate_tab` — navigate to a specific tab
- `enter_replay` — enter replay mode for a time range
- `export_chart` — export chart as PNG or CSV
- `clear_ai_annotations` — clear all AI highlights and overlays
"""


def _build_tool_catalog_text() -> str:
    return TOOL_CATALOG_TEXT


def _build_walkthrough_prompt() -> str:
    """Build the Phase E Interact mode walkthrough prompt.

    Instructs the LLM to produce both analysis text AND a structured
    multi-step walkthrough plan embedded in `<walkthrough>` tags.
    """
    parts = [
        'Interact mode — you are in a **guided analysis walkthrough**.',
        'Your job is to BOTH analyze the data AND create an actionable walkthrough',
        'the user can follow step-by-step on the chart.',
        '',
        '## How the Walkthrough Works',
        '1. Write your **analysis content** first — market context, technical signals, key levels.',
        '2. At the very end, include a `<walkthrough>` block with structured JSON.',
        "3. The frontend executes each step one-at-a-time with Next/Prev navigation.",
        '4. After all steps, a recap is shown with Replay/Keep/Revert.',
        '',
        '## Walkthrough JSON Format',
        'Wrap the plan in `<walkthrough>` tags at the end of your response:',
        '',
        "```",
        "<walkthrough>",
        '{"title": "Brief title",',
        ' "summary": "Recap shown after all steps.",',
        ' "steps": [',
        '   {',
        '     "explanation": "What we\'re doing and why (WHY + WHAT shows + WHAT means + LOOK FOR).",',
        '     "keep_effects": false,',
        '     "chart_freeze": true,',
        '     "actions": [',
        '       {"type": "add_indicator", "params": {"indicator": "rsi"}},',
        '       {"type": "set_timeframe", "params": {"timeframe": "4h"}}',
        '     ]',
        '   }',
        ' ]',
        '}',
        "</walkthrough>",
        "```",
        '',
        '## Step-by-Step Reasoning Chain',
        'For EVERY action in a step, include this in the explanation:',
        '1. **WHY** this action — what question does it answer?',
        '2. **WHAT it shows** — what will the user see on screen?',
        '3. **WHAT it means** — how to interpret the result',
        '4. **WHAT to look for next** — what confirms or refutes the thesis',
        '',
        'Example:',
        '> "Draw Fibonacci retracement from swing low to swing high. **WHY**: Identify potential support/resistance levels. **WHAT it shows**: Levels at $62,500 (0.382), $61,200 (0.5), $59,800 (0.618). **WHAT it means**: Price often finds support at these Fibonacci levels. **LOOK FOR**: Whether price bounces off the 0.618 level."',
        '',
        '## Multi-Action Steps',
        "- Each step can have MULTIPLE simultaneous actions (e.g., add RSI + draw trendline + highlight zone).",
        "- Use `keep_effects: false` to clear previous step's drawings/highlights before applying this step's.",
        "- Use `keep_effects: true` when building on previous step (e.g., step 1 adds RSI, step 2 adds trendline on same data).",
        '',
        '## Drawing Tools (MAIN VALUE of walkthroughs)',
        'Use drawing tools HEAVILY to visualize analysis — this is what makes',
        'walkthroughs valuable vs plain text answers.',
        '- **draw_trendline**: Connect two points. Params: from_time, from_price, to_time, to_price, color, style.',
        '- **draw_tool**: Generic drawing. Params: tool (trendline/fibonacci/rectangle/cursor), points [{time,price}], text.',
        '- **create_annotation**: Text note. Params: time, price, text.',
        '- **highlight_candles**: Highlight candle range. Params: start_time, end_time, label.',
        '- **highlight_contextual_zone**: Analytical zone. Params: zone_type, direction, label, candle_count.',
        '',
        '**Drawing guidelines**:',
        '- Draw trendlines for EVERY support/resistance level you identify.',
        '- Use Fibonacci retracements for key reversal zones.',
        '- Use rectangles to highlight consolidation or accumulation ranges.',
        '- Use annotations to label key price levels with explanations.',
        '- Mark breakout/breakdown levels with horizontal lines or highlights.',
        '- Visualize divergences by connecting RSI peaks to price peaks with trendlines.',
        '',
        _build_tool_catalog_text(),
        '',
        '## Final Recap Structure',
        'After all steps complete, the summary becomes the final recap.',
        'The recap should include:',
        '1. **What was done** — a brief summary of each step and action taken.',
        '2. **Key points & information** — the most important findings from the analysis.',
        '3. **Conclusion** — what the analysis suggests about the current market state.',
        '',
        '## Action Persistence Rules',
        "- Between steps with `keep_effects: false`, drawings and highlights from previous step are cleared.",
        '- Indicators and timeframe changes accumulate across steps (not reset).',
        '- Final recap clears all temporary drawings/highlights.',
        '',
        '## Good Practices',
        '- 3-5 steps ideal.',
        '- First step: set up chart (timeframe, indicators).',
        '- Middle steps: perform analysis (drawings, Fibonacci, annotations).',
        '- Final step: highlight conclusion and prepare for recap.',
        '- Only include walkthrough for substantive analysis, not simple price checks.',
    ]
    return '\n'.join(parts)


SYNTHESIS_SYSTEM_PROMPT = """You are LMView AI, a bilingual (English/Vietnamese) crypto technical analysis assistant.

## Core Rules
1. Respond in the user's language — detect from their message. Never mix languages.
2. Use markdown: headings (`###`), lists, bold for key values (prices, % changes, signals).
3. Convert raw variable names to human-readable (sma20 → 20-period SMA, rsi → RSI, macd → MACD).
4. Prefix USD prices with `$` (e.g. **$62,745**).
5. NEVER give buy/sell recommendations or price predictions.
6. NEVER execute code, SQL, or shell commands.
7. Do NOT add disclaimers — appended server-side.

## Synthesis Rules
- Synthesize the expert analysis data (provided as system messages) into a coherent response.
- Prioritize what's most relevant to the user query.
- Acknowledge data limitations if caveats are present.
- State confidence honestly — don't fabricate precision.

## Response Structure (adapt to query)
When relevant: Market Context → Technical Signals → Order Flow → News/Sentiment → Knowledge → Key Levels → Risk Notes
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
    context_needs = state.get("context_needs")

    # Build context sections from expert outputs
    context_sections = _build_context_sections(expert_outputs, chart_context, data_caveats)

    # Build the prompt messages
    from backend.models.ai.providers import LLMMessage, LLMCompletionRequest

    messages: List[LLMMessage] = []

    # System prompt
    now_utc = datetime.now(timezone.utc)
    user_tz_str = state.get("user_timezone")
    user_time_info = ""
    if user_tz_str:
        try:
            from zoneinfo import ZoneInfo
            user_tz = ZoneInfo(user_tz_str)
            now_user = now_utc.astimezone(user_tz)
            user_time_info = (
                f"- User's local timezone: {user_tz_str}\n"
                f"- User's local time: {now_user.isoformat()}\n"
            )
        except Exception:
            pass

    runtime = (
        f"\n## Runtime Context\n"
        f"- Current server time (UTC): {now_utc.isoformat()}\n"
        f"- Current epoch milliseconds: {int(now_utc.timestamp() * 1000)}\n"
        f"{user_time_info}"
        f"- Chart times are live runtime data — do not reject timestamps past training cutoff.\n"
    )
    system_content = SYNTHESIS_SYSTEM_PROMPT + runtime
    if language and language.lower() in ("vi", "vietnamese"):
        system_content += "\nThe user prefers Vietnamese. Think through your analysis in **English** first, then write your final response entirely in Vietnamese. Do NOT mix English into the response body.\n"
    elif language and language.lower() in ("en", "english"):
        system_content += "\nThe user prefers English. Respond in English only. Do NOT mix Vietnamese into the response.\n"

    messages.append(LLMMessage(role="system", content=system_content))

    # Expert data as system context
    if context_sections:
        messages.append(LLMMessage(
            role="system",
            content="## Expert Analysis Data\n" + context_sections,
            name="expert_data",
        ))

    # Context needs awareness — what data was requested vs available
    if context_needs:
        cn = context_needs
        cn_lines = ["## Data Requirements"]
        if cn.symbols:
            cn_lines.append(f"- Requested symbols: {', '.join(cn.symbols)}")
        if cn.timeframes:
            cn_lines.append(f"- Requested timeframes: {', '.join(cn.timeframes)}")
        if cn.indicators:
            cn_lines.append(f"- Requested indicators: {', '.join(cn.indicators)}")
        if cn.needs_news:
            cn_lines.append("- News/sentiment data was requested")
        if cn.needs_orderbook:
            cn_lines.append("- Order book depth was requested")
        if cn.needs_historical_prices:
            cn_lines.append("- Historical price data was requested")
        if cn.needs_drawings:
            cn_lines.append("- Existing drawings were requested")
        if not cn.needs_rag:
            cn_lines.append("- Knowledge base was NOT requested (simple price query)")
        if cn.unretrievable:
            cn_lines.append(f"- ⚠ Data that could NOT be retrieved: {', '.join(cn.unretrievable)}")
        if cn.fallback_description:
            cn_lines.append(f"- Fallback strategy: {cn.fallback_description}")
        if cn.unretrievable:
            cn_lines.append(
                "\nIf some requested data is unavailable, use the closest available information "
                "and clearly state what you\'re using instead. Don\'t pretend the unavailable data exists."
            )
        messages.append(LLMMessage(
            role="system",
            content="\n".join(cn_lines),
            name="context_needs",
        ))

    # ── Phase C: Session Memory injection ──────────────────────────────
    session_id = state.get("session_id", "")
    user_id = state.get("user_id", "")
    if session_id and user_id:
        try:
            from ai_service.persistence import chat_store
            meta = await chat_store.get_session_metadata(session_id, user_id)
            if meta:
                memory = meta.get("session_memory", {})
                if memory and memory.get("findings"):
                    findings = memory["findings"][-3:]  # last 3 only
                    mem_lines = ["## Previous Session Context"]
                    mem_lines.append("The following were established in earlier turns:")
                    for f in findings:
                        mem_lines.append(f"- {f}")
                    if memory.get("compacted"):
                        mem_lines.append(
                            f"\n*Note: This session has {memory.get('turn_count', 0)} prior exchanges. "
                            "Older conversation history has been compacted — key points preserved above.*"
                        )
                    messages.append(LLMMessage(
                        role="system",
                        content="\n".join(mem_lines),
                        name="session_memory",
                    ))
        except Exception:
            pass

    # Interact mode policy — Phase E: multi-step walkthrough
    if mode == "interact":
        interact_prompt = _build_walkthrough_prompt()
        messages.append(LLMMessage(
            role="system",
            content=interact_prompt,
            name="interaction_policy",
        ))
    # Conversation history — cap at 2000 chars total
    hist_chars = 0
    for msg in chat_history[-10:]:
        content = msg.get("content", "")
        if hist_chars + len(content) > 2000:
            remaining = 2000 - hist_chars
            if remaining > 100:
                content = content[:remaining] + "..."
            else:
                break
        hist_chars += len(content)
        messages.append(LLMMessage(
            role=msg.get("role", "user"),
            content=content,
        ))

    # User message
    messages.append(LLMMessage(role="user", content=user_query))

    from ai_service.providers.router import get_provider_router
    from ai_service.config import load_settings
    from ai_service.actions.tool_definitions import get_openai_tools

    settings = load_settings()

    # Pass tools parameter in Interact mode for native function calling
    tools_param = None
    tool_choice = None
    if mode == "interact":
        tools_param = get_openai_tools()
        tool_choice = "auto"

    llm_request = LLMCompletionRequest(
        messages=messages,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
        top_p=settings.top_p,
        metadata={"mode": mode, "node": "synthesis"},
        tools=tools_param,
        tool_choice=tool_choice,
    )

    provider_router = get_provider_router()
    # Use reserved tier for synthesis (higher quality), context/classification uses standard
    effective_tier = state.get("selected_tier") or "reserved"
    llm_response, routing = await provider_router.route_completion(
        llm_request,
        selected_model=state.get("selected_model"),
        selected_tier=effective_tier,
    )

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
                # Auto-approve safe read-only / educational actions
                req_app = act_type not in {
                    "highlight_section", "clear_ai_annotations", "start_walkthrough"
                }

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
    """Build formatted context from all expert outputs for the LLM with budgeting.

    Budget allocation (Total MAX_CHARS = 8000):
    1. Data Caveats (Vital)
    2. Proposed Chart Actions (Vital)
    3. Structured Data Tables (Vital)
    4. RAG Chunks (High priority)
    5. Narrative Sections (Medium priority)

    Guarantees structured tables/caveats/actions are never truncated,
    while RAG and narratives are trimmed intelligently to fit the budget.
    """
    MAX_CHARS = 8000

    # 1. Build Caveats
    caveats_parts = []
    if data_caveats:
        caveats_parts.append("### ⚠️ Data Caveats")
        for caveat in data_caveats:
            caveats_parts.append(f"- {caveat}")
        caveats_parts.append("")
    caveats_text = "\n".join(caveats_parts)

    # 2. Build Actions
    actions_parts = []
    ci = expert_outputs.get("chart_interaction")
    if ci and ci.structured_data.get("proposed_actions"):
        actions = ci.structured_data["proposed_actions"]
        actions_parts.append(f"### Proposed Chart Actions ({len(actions)})")
        for a in actions:
            tool = a.get("tool") or a.get("action_type", "?")
            params = a.get("params", {})
            reason = a.get("reason", "")
            actions_parts.append(f"- `{tool}`: {reason}")
            if params:
                actions_parts.append(f"  Params: {params}")
        actions_parts.append("")
    actions_text = "\n".join(actions_parts)

    # 3. Build Structured Data
    structured_parts = []

    # Technical Indicators
    ta = expert_outputs.get("technical_analysis")
    if ta and not ta.error:
        indicators = ta.structured_data.get("indicators", {})
        if indicators:
            structured_parts.append("### Technical Indicators (Raw Values)")
            structured_parts.append(_format_indicator_table(indicators))
            structured_parts.append("")

            signals = ta.structured_data.get("signals", [])
            if signals:
                structured_parts.append("**Detected Signals:**")
                for sig in signals:
                    bias_marker = "🟢" if sig.get("bias") == "bullish" else ("🔴" if sig.get("bias") == "bearish" else "⚪")
                    sig_str = sig.get("signal", "").replace("_", " ")
                    structured_parts.append(f"- {bias_marker} {sig.get('indicator', '?')}: {sig_str}")
                    val = sig.get("value")
                    if val is not None:
                        structured_parts[-1] += f" (value: {val})"
                structured_parts.append("")

            sr = ta.structured_data.get("support_resistance")
            if sr:
                structured_parts.append("**Support & Resistance Levels:**")
                current = sr.get("current_price")
                if current is not None:
                    structured_parts.append(f"- Current price: ${current:,.2f}" if current >= 1 else f"- Current price: ${current:.6f}")
                ns = sr.get("nearest_support")
                if ns is not None:
                    structured_parts.append(f"- Nearest support: ${ns:,.2f}" if ns >= 1 else f"- Nearest support: ${ns:.6f}")
                nr = sr.get("nearest_resistance")
                if nr is not None:
                    structured_parts.append(f"- Nearest resistance: ${nr:,.2f}" if nr >= 1 else f"- Nearest resistance: ${nr:.6f}")
                for label, levels in [("Support", sr.get("support_levels", [])), ("Resistance", sr.get("resistance_levels", []))]:
                    if levels:
                        formatted = [f"${l:,.2f}" if l >= 1 else f"${l:.6f}" for l in levels]
                        structured_parts.append(f"- {label} levels: {', '.join(formatted)}")
                range_pct = sr.get("range_pct")
                if range_pct is not None:
                    structured_parts.append(f"- Range (S-R): {range_pct:.2f}%")
                structured_parts.append("")

    # Market Data
    md = expert_outputs.get("market_data")
    if md and not md.error:
        structured_parts.append("### Market Data")
        ticker = md.structured_data.get("ticker", {})
        if ticker:
            close = ticker.get("close")
            change = ticker.get("change_pct")
            if close is not None:
                close_str = f"${float(close):,.2f}" if float(close) >= 1 else f"${float(close):.6f}"
                change_str = f" ({change:+.2f}%)" if change is not None else ""
                structured_parts.append(f"- Price: {close_str}{change_str}")
            for k in ("open", "high", "low"):
                v = ticker.get(k)
                if v is not None:
                    v_str = f"${float(v):,.2f}" if float(v) >= 1 else f"${float(v):.6f}"
                    structured_parts.append(f"- {k.capitalize()}: {v_str}")
            vol = ticker.get("volume")
            if vol is not None:
                structured_parts.append(f"- Volume: {float(vol):,.0f}")

        ob = md.structured_data.get("orderbook", {})
        if ob:
            bid = ob.get("best_bid")
            ask = ob.get("best_ask")
            spread = ob.get("spread")
            imbalance = ob.get("imbalance")
            if bid is not None and ask is not None:
                structured_parts.append(f"- Order book: Bid {bid} / Ask {ask}")
                if spread is not None:
                    structured_parts.append(f"  Spread: {spread:.4f}")
            if imbalance is not None:
                imb_val = float(imbalance)
                side = "buy-heavy 🟢" if imb_val > 0.3 else ("sell-heavy 🔴" if imb_val < -0.3 else "balanced ⚪")
                structured_parts.append(f"  Imbalance: {imb_val:.4f} ({side})")

        trades = md.structured_data.get("trades", {})
        if trades:
            is_true = trades.get("is_true_trade_tape", False)
            structured_parts.append(f"- Trade data: {'true tape' if is_true else 'ticker-derived (approximate)'}")
            count = trades.get("recent_count")
            if count is not None:
                structured_parts.append(f"  Recent trades: {count}")

        market_ov = md.structured_data.get("market_overview", {})
        if market_ov and not market_ov.get("is_placeholder", True):
            btc_dom = market_ov.get("btc_dominance")
            if btc_dom is not None:
                structured_parts.append(f"- BTC dominance: {btc_dom:.2f}%")
            tmc = market_ov.get("total_market_cap")
            if tmc is not None:
                structured_parts.append(f"- Total market cap: ${float(tmc):,.0f}")
        structured_parts.append("")

    # News & Sentiment Structured
    ns = expert_outputs.get("news_sentiment")
    if ns and not ns.error:
        ns_data = ns.structured_data
        sentiment = ns_data.get("sentiment_summary", {})
        if sentiment:
            structured_parts.append("### News & Sentiment")
            direction = sentiment.get("direction", "neutral")
            emoji = "🟢" if direction == "positive" else ("🔴" if direction == "negative" else "⚪")
            structured_parts.append(f"- Overall: {emoji} {direction}")
            avg = sentiment.get("avg_score")
            if avg is not None:
                structured_parts.append(f"  Score: {avg:.4f}")
            pos = sentiment.get("positive_count", 0)
            neg = sentiment.get("negative_count", 0)
            neu = sentiment.get("neutral_count", 0)
            if pos or neg or neu:
                structured_parts.append(f"  Distribution: +{pos} / ={neu} / -{neg}")

        articles = ns_data.get("articles", [])
        if articles:
            structured_parts.append(f"**Top headlines ({len(articles)}):**")
            for a in articles:
                sent_label = a.get("sentiment", "neutral")
                sent_emoji = "🟢" if sent_label == "positive" else ("🔴" if sent_label == "negative" else "⚪")
                structured_parts.append(f"- {sent_emoji} {a.get('title', '?')}")

        risk_events = ns_data.get("risk_events", [])
        if risk_events:
            structured_parts.append("⚠️ **Risk events:**")
            for event in risk_events:
                structured_parts.append(f"- {event}")

        trending = ns_data.get("trending_symbols", [])
        if trending:
            structured_parts.append(f"**Trending symbols:** {', '.join(t.get('symbol', '?') for t in trending[:5])}")
        structured_parts.append("")

    structured_text = "\n".join(structured_parts)

    # Calculate remaining budget for RAG and Narratives
    vital_chars = len(caveats_text) + len(actions_text) + len(structured_text)
    remaining_budget = max(500, MAX_CHARS - vital_chars)

    # 4. Build RAG Chunks (Intelligent truncation)
    rag_parts = []
    rag = expert_outputs.get("rag_knowledge")
    if rag and rag.structured_data.get("total_retrieved", 0) > 0:
        chunks = rag.structured_data.get("chunks", [])
        total_retrieved = rag.structured_data['total_retrieved']
        rag_parts.append(f"### Knowledge Base ({total_retrieved} entries retrieved)")

        # Budget allocation for RAG: up to 40% of remaining budget
        rag_budget = int(remaining_budget * 0.40)
        current_rag_len = len(rag_parts[0])

        for i, chunk in enumerate(chunks[:5], 1):
            source = chunk.get("source", "?")
            title = chunk.get("title", "?")
            score = chunk.get("score", 0)
            text = chunk.get("text", "")
            heading = chunk.get("heading", "")
            credibility = chunk.get("credibility_level", "") or ""
            source_type = chunk.get("source_type", "") or ""
            heading_str = f" — *{heading}*" if heading else ""
            credibility_badge = f" [{credibility}]" if credibility else ""
            type_badge = f" ({source_type})" if source_type else ""

            # Cap individual chunk text at 800 chars to save space
            if len(text) > 800:
                text = text[:800] + "\n[...truncated...]"

            chunk_header = f"[{i}] **{title}**{credibility_badge}{type_badge} (source: {source}, relevance: {score:.2f}){heading_str}"
            chunk_body = f"    {text}"
            chunk_item = f"{chunk_header}\n{chunk_body}\n"

            # Check if this chunk fits the RAG budget
            if current_rag_len + len(chunk_item) > rag_budget:
                rag_parts.append(f"\n[... {total_retrieved - i + 1} more knowledge entries omitted to preserve token budget ...]")
                break

            rag_parts.append(chunk_item)
            current_rag_len += len(chunk_item)

        # Grounding instruction
        grounding_text = (
            "\n**Grounding rule:** The Knowledge Base entries above are the authoritative "
            "source for questions about LMView features, indicators, drawing tools, and "
            "system capabilities. If the user asks about a feature NOT described in these "
            "entries, state that the feature does not exist. Do NOT guess or hallucinate "
            "UI steps for unknown features.\n"
            "If any information in the Knowledge Base conflicts with your internal training "
            "data, PREFER the Knowledge Base and explicitly note the conflict."
        )
        rag_parts.append(grounding_text)
        rag_parts.append("")

    rag_text = "\n".join(rag_parts)

    # Update remaining budget for Narratives
    remaining_budget = max(500, MAX_CHARS - (vital_chars + len(rag_text)))

    # 5. Build Narratives (Intelligent truncation per active section)
    narrative_sections = []
    for expert_name, section_title in [
        ("technical_analysis", "### Technical Analysis (Narrative)"),
        ("market_data", "### Market Data (Narrative)"),
        ("news_sentiment", "### News & Sentiment (Narrative)"),
        ("general", "### General Context"),
    ]:
        expert = expert_outputs.get(expert_name)
        if expert and expert.content and not expert.error:
            narrative_sections.append((section_title, expert.content))

    narrative_parts = []
    if narrative_sections:
        # Divide remaining budget equally among active narratives
        share_per_narrative = int(remaining_budget / len(narrative_sections))
        # Keep a minimum of 400 chars per narrative if possible
        share_per_narrative = max(400, share_per_narrative)

        for title, content in narrative_sections:
            narrative_parts.append(title)
            if len(content) > share_per_narrative:
                truncated_content = content[:share_per_narrative] + "\n[...narrative truncated for space...]"
                narrative_parts.append(truncated_content)
            else:
                narrative_parts.append(content)
            narrative_parts.append("")

    narratives_text = "\n".join(narrative_parts)

    # Combine everything
    all_sections = [
        caveats_text,
        actions_text,
        structured_text,
        rag_text,
        narratives_text
    ]

    result = "\n".join(filter(None, all_sections))

    # Safety net cap
    if len(result) > MAX_CHARS:
        result = result[:MAX_CHARS - 3] + "..."

    return result


def _format_indicator_table(indicators: Dict[str, Any]) -> str:
    """Format indicator dict into a clean scannable table."""
    lines = []
    for key, value in indicators.items():
        if value is None:
            continue
        try:
            val = float(value)
        except (ValueError, TypeError):
            lines.append(f"- {key}: {value}")
            continue

        # Skip non-indicator keys
        if key in ("candle_open", "candle_close", "candle_high", "candle_low", "candle_volume",
                    "bb_width", "atr", "atr14"):
            continue

        # Human-readable names
        name_map = {
            "rsi": "RSI(14)", "rsi14": "RSI(14)",
            "macd": "MACD", "macd_signal": "MACD Signal", "macd_histogram": "MACD Histogram",
            "sma20": "SMA(20)", "sma50": "SMA(50)",
            "ema12": "EMA(12)", "ema26": "EMA(26)",
            "bb_upper": "Bollinger Upper", "bollinger_upper": "Bollinger Upper",
            "bb_lower": "Bollinger Lower", "bollinger_lower": "Bollinger Lower",
            "bb_middle": "Bollinger Middle", "bollinger_middle": "Bollinger Middle",
            "vwap": "VWAP",
            "volume": "Volume", "volume_sma20": "Volume SMA(20)",
        }
        display_name = name_map.get(key, key)

        # Format with appropriate precision
        if key in ("rsi", "rsi14"):
            lines.append(f"- {display_name}: {val:.1f} " + _rsi_label(val))
        elif key in ("macd", "macd_signal", "macd_histogram", "bb_width"):
            lines.append(f"- {display_name}: {val:.4f}")
        elif key in ("volume", "volume_sma20"):
            lines.append(f"- {display_name}: {val:,.0f}")
        elif "margin" in key or "pnl" in key:
            lines.append(f"- {display_name}: {val:,.2f}%")
        elif val >= 1:
            lines.append(f"- {display_name}: ${val:,.2f}" if "volume" not in key else f"- {display_name}: {val:,.0f}")
        else:
            lines.append(f"- {display_name}: ${val:.6f}")
    return "\n".join(lines)


def _rsi_label(rsi_val: float) -> str:
    """Label for RSI value."""
    if rsi_val <= 30:
        return "(oversold 🟢)"
    elif rsi_val >= 70:
        return "(overbought 🔴)"
    elif rsi_val >= 60:
        return "(strong, approaching overbought)"
    elif rsi_val <= 40:
        return "(weak, approaching oversold)"
    return "(neutral)"


async def synthesize_response_stream(
    state: AgentState,
) -> AsyncGenerator[str, None]:
    """Streaming response synthesis — yields SSE token events.

    Builds context from expert outputs (same as batch), makes a single
    streaming LLM call, and yields tokens as they arrive.
    After streaming completes, applies output guard and yields final metadata.
    """
    expert_outputs = state.get("expert_outputs", {})
    user_query = state.get("user_query", "")
    language = state.get("language")
    chart_context = state.get("chart_context")
    chat_history = state.get("chat_history", [])
    data_caveats = state.get("data_caveats", [])
    mode = state.get("mode", "ask")
    context_needs = state.get("context_needs")

    # Build context sections
    context_sections = _build_context_sections(expert_outputs, chart_context, data_caveats)

    from backend.models.ai.providers import LLMMessage, LLMCompletionRequest

    messages: List[LLMMessage] = []

    # System prompt
    now_utc = datetime.now(timezone.utc)
    user_tz_str = state.get("user_timezone")
    user_time_info = ""
    if user_tz_str:
        try:
            from zoneinfo import ZoneInfo
            user_tz = ZoneInfo(user_tz_str)
            now_user = now_utc.astimezone(user_tz)
            user_time_info = (
                f"- User's local timezone: {user_tz_str}\n"
                f"- User's local time: {now_user.isoformat()}\n"
            )
        except Exception:
            pass

    runtime = (
        f"\n## Runtime Context\n"
        f"- Current server time (UTC): {now_utc.isoformat()}\n"
        f"- Current epoch milliseconds: {int(now_utc.timestamp() * 1000)}\n"
        f"{user_time_info}"
        f"- Chart times are live runtime data — do not reject timestamps past training cutoff.\n"
    )
    system_content = SYNTHESIS_SYSTEM_PROMPT + runtime
    if language and language.lower() in ("vi", "vietnamese"):
        system_content += "\nThe user prefers Vietnamese. Think through your analysis in **English** first, then write your final response entirely in Vietnamese. Do NOT mix English into the response body.\n"

    messages.append(LLMMessage(role="system", content=system_content))

    # Expert data as system context
    if context_sections:
        messages.append(LLMMessage(
            role="system",
            content="## Expert Analysis Data\n" + context_sections,
            name="expert_data",
        ))

    # Context needs awareness — what data was requested vs available
    if context_needs:
        cn = context_needs
        cn_lines = ["## Data Requirements"]
        if cn.symbols:
            cn_lines.append(f"- Requested symbols: {', '.join(cn.symbols)}")
        if cn.timeframes:
            cn_lines.append(f"- Requested timeframes: {', '.join(cn.timeframes)}")
        if cn.indicators:
            cn_lines.append(f"- Requested indicators: {', '.join(cn.indicators)}")
        if cn.needs_news:
            cn_lines.append("- News/sentiment data was requested")
        if cn.needs_orderbook:
            cn_lines.append("- Order book depth was requested")
        if cn.needs_historical_prices:
            cn_lines.append("- Historical price data was requested")
        if cn.needs_drawings:
            cn_lines.append("- Existing drawings were requested")
        if not cn.needs_rag:
            cn_lines.append("- Knowledge base was NOT requested (simple price query)")
        if cn.unretrievable:
            cn_lines.append(f"- ⚠ Data that could NOT be retrieved: {', '.join(cn.unretrievable)}")
        if cn.fallback_description:
            cn_lines.append(f"- Fallback strategy: {cn.fallback_description}")
        if cn.unretrievable:
            cn_lines.append(
                "\nIf some requested data is unavailable, use the closest available information "
                "and clearly state what you\'re using instead. Don\'t pretend the unavailable data exists."
            )
        messages.append(LLMMessage(
            role="system",
            content="\n".join(cn_lines),
            name="context_needs",
        ))

    # ── Phase C: Session Memory injection (stream) ─────────────────────
    session_id = state.get("session_id", "")
    user_id = state.get("user_id", "")
    if session_id and user_id:
        try:
            from ai_service.persistence import chat_store
            meta = await chat_store.get_session_metadata(session_id, user_id)
            if meta:
                memory = meta.get("session_memory", {})
                if memory and memory.get("findings"):
                    findings = memory["findings"][-3:]  # last 3 only
                    mem_lines = ["## Previous Session Context"]
                    mem_lines.append("The following were established in earlier turns:")
                    for f in findings:
                        mem_lines.append(f"- {f}")
                    if memory.get("compacted"):
                        mem_lines.append(
                            f"\n*Note: This session has {memory.get('turn_count', 0)} prior exchanges. "
                            "Older conversation history has been compacted — key points preserved above.*"
                        )
                    messages.append(LLMMessage(
                        role="system",
                        content="\n".join(mem_lines),
                        name="session_memory",
                    ))
        except Exception:
            pass

        # Interact mode policy — Phase E: multi-step walkthrough
    if mode == "interact":
        interact_prompt = _build_walkthrough_prompt()
        messages.append(LLMMessage(
            role="system",
            content=interact_prompt,
            name="interaction_policy",
        ))
    # Conversation history — cap at 2000 chars total
    hist_chars = 0
    for msg in chat_history[-10:]:
        content = msg.get("content", "")
        if hist_chars + len(content) > 2000:
            remaining = 2000 - hist_chars
            if remaining > 100:
                content = content[:remaining] + "..."
            else:
                break
        hist_chars += len(content)
        messages.append(LLMMessage(
            role=msg.get("role", "user"),
            content=content,
        ))

    # User message
    messages.append(LLMMessage(role="user", content=user_query))

    from ai_service.providers.router import get_provider_router
    from ai_service.config import load_settings
    from ai_service.actions.tool_definitions import get_openai_tools

    settings = load_settings()

    # Pass tools parameter in Interact mode
    tools_param = None
    tool_choice = None
    if mode == "interact":
        tools_param = get_openai_tools()
        tool_choice = "auto"

    llm_request = LLMCompletionRequest(
        messages=messages,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
        top_p=settings.top_p,
        metadata={"mode": mode, "node": "synthesis_stream"},
        tools=tools_param,
        tool_choice=tool_choice,
    )

    provider_router = get_provider_router()
    accumulated = ""

    async for event in provider_router.route_completion_stream(
        llm_request,
        selected_model=state.get("selected_model"),
        selected_tier=state.get("selected_tier"),
    ):
        yield event
        # Accumulate for post-hoc guard check
        try:
            ev = json.loads(event)
            if ev.get("content") and not ev.get("done"):
                accumulated += ev["content"]
        except (json.JSONDecodeError, TypeError):
            pass

    # Apply output guard on full accumulated response (post-hoc)
    from ai_service.safety.output_guard import guard_output
    guard_result = guard_output(accumulated, language=language)
    final_content = guard_result["content"]
    guard_warnings = list(guard_result["warnings"])

    # Yield final metadata with guard results
    metadata_event = json.dumps({
        "event": "metadata",
        "guard_warnings": guard_warnings,
        "content": final_content,
        "done": True,
    })
    yield metadata_event
