"""
Tour Planner — converts expert analysis into step-by-step guided tours for Interact mode.

Runs after the full pipeline completes (scope → experts → synthesis). Takes
all expert outputs + synthesized response and plans a multi-step chart tour.

Each step maps to an action_type supported by the frontend action system.
The user progresses through steps at their own pace.

Interact mode is meant to be visually rich: the LLM proposes chart actions
that the frontend executes *outside* the chat panel (highlights, drawings,
indicator reveals, panel switches, annotations) and only returns to the
chat with a final recap once all steps are done.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional

from backend.models.ai.tour import TourPlan, TourStepAction
from ai_service.tours.tour_templates import (
    WORKSPACE_OVERVIEW_TOUR,
    INDICATOR_TUTORIAL_TOUR,
)

logger = logging.getLogger("ai_service.agents.experts.tour_planner")

# ── Supported action types the tour planner can emit ─────────────────────────
# These must match handlers in frontend ``AiActionProvider`` registry. Order
# is informational only — the LLM picks the right one for each step.

SUPPORTED_ACTIONS = [
    # UI navigation
    "highlight_section",        # dim everything except a UI section
    "highlight_chart_area",     # highlight a rect within the chart canvas
    "view_section",             # open and highlight a major app section
    # Chart canvas decorations
    "highlight_candles",        # highlight a candle range (index-based)
    "draw_tool",                # select drawing tool + draw on chart
    "draw_trendline",           # alias for draw_tool/trendline
    "create_annotation",        # text label on chart at time/price
    "clear_drawings",           # remove AI-placed drawings
    "delete_drawing",           # remove one specific drawing
    "set_drawing_color",        # recolor a drawing
    # Indicators
    "add_indicator",            # show an indicator
    "remove_indicator",         # hide an indicator
    "configure_indicator",      # update period / color / etc.
    # Chart state changes
    "set_timeframe",
    "set_chart_type",
    "set_symbol",               # switch market (e.g. BTCUSDT -> ETHUSDT)
    "zoom_chart",
    "scroll_chart",
    "scroll_chart_to_time",     # scroll to a specific timestamp
    "reset_chart_view",         # reset zoom + scroll
    # Right-panel / app navigation (chart + orderbook + trades + news)
    "open_panel",               # open right panel with a target tab
    "close_panel",              # close right panel
    "switch_panel_tab",         # switch between watchlist/orderBook/trades
    "switch_app_view",          # switch between charts/marketsNews/screener
    "open_settings",            # open settings modal
    "close_settings",           # close settings modal
    "fetch_historical_prices",  # load historical candles for a range
    # Tour control
    "end_tour",                 # cancel the active tour
]

# ── LLM Prompt ─────────────────────────────────────────────────────────────────

TOUR_PLANNER_SYSTEM_PROMPT = """You are LMView's chart analysis tour guide. Your job is to convert raw market analysis into a step-by-step *visual* tour that teaches the user about the current market situation through hands-on chart exploration.

## Decision: tour or no tour?
* Lean toward planning a tour whenever the user asks for visual information ("show me", "analyze", "compare", "what does X look like") or about a specific market setup. Most user questions in Interact mode deserve at least a short visual tour.
* For "how to use LMView" / "what can LMView do" / "demo" → return a short 3-5 step walkthrough of the app's UI sections.
* If the user is asking a pure-textual factual question with no chart context (e.g. "what is the formula for RSI", "what does HODL mean") AND the analysis has no concrete visual element → return `{"tour_plan": null}` and let Ask mode handle the chat. Do NOT pad with empty steps.
* When in doubt, plan a tour. A short focused tour is better than no tour at all.

## Hard rules
1. 3-6 steps. Each step has ONE action_type + a 1-2 sentence `explanation` (shown to the user as the step text).
2. The `explanation` field is what the user reads — it MUST be specific to the current market situation. Never use boilerplate like "The chart shows real-time OHLCV candlesticks" or "Let's look at the recent price action" unless those are literally the only facts available.
3. **Never repeat the same action_type in consecutive steps.** If you want to add two indicators, put them in ONE step using `add_indicator` with both keys OR pick the more important one. Two back-to-back "Add indicator" steps is noise.
4. Start with orientation (highlight chart area / latest candles), then reveal the key signal (indicator, drawing, annotation), then optionally end with a panel switch if it adds value.
5. The `tour_id` MUST be `lmview-overview` for "how to use LMView" type queries and `ai-tour-{epoch}` for everything else. The backend will rewrite it.
6. Never use `synthesized_response` text verbatim as `explanation`. Paraphrase; add market-specific context; reference specific price levels or signals from the analysis.
7. Never propose actions that change the user's data (no orders, no deletes).
8. If a step would not visually change anything (e.g. set_timeframe to the same timeframe), skip it.
9. When the user asks about the order book, liquidity, bids/asks → use `open_panel target=orderBook` and `set_symbol` if needed. Do NOT refuse just because the synthesis says "I cannot access real-time data" — the chart actions dispatch directly to the UI, not via the LLM.
10. When the user asks to compare multiple markets → plan `set_symbol` steps for each, with annotations or highlights between.
11. When the user asks about news/macro/sentiment → plan `switch_app_view view=marketsNews` near the end.

## Output format
Respond with ONLY valid JSON. No markdown, no code fences, no explanation outside JSON.
{{
  "tour_plan": {{
    "title": "Short tour title that names the market/setup",
    "steps": [
      {{
        "action_type": "...",
        "params": {{...}},
        "explanation": "Specific educational explanation referencing the current setup..."
      }}
    ],
    "summary": "Concise recap of what the user just saw, specific to the analysis"
  }}
}}
or
{{"tour_plan": null}}

## Action types and their params
{action_params}

## Few-shot examples

### Example 1: "Analyze BTCUSDT current price action"
Analysis: BTC is at $67,200, bouncing off the $66,800 support, RSI 58 (neutral), volume declining on the bounce, MACD just crossed bullishly on 4H.
```json
{{
  "tour_plan": {{
    "title": "BTCUSDT: Bounce off $66,800 support",
    "steps": [
      {{
        "action_type": "highlight_candles",
        "params": {{"from_index": -12, "to_index": -1, "label": "Last 4H of action", "message": "The bounce off $66,800 is forming a short base."}},
        "explanation": "The last 4 hours of price action: BTC bounced cleanly off the $66,800 support, putting in a higher low at $67,100."
      }},
      {{
        "action_type": "add_indicator",
        "params": {{"indicator": "rsi"}},
        "explanation": "RSI is at 58 — neutral, but the recent uptick from 42 suggests momentum is shifting without being overbought yet."
      }},
      {{
        "action_type": "create_annotation",
        "params": {{"time": 1719000000000, "price": 66800, "text": "Support $66,800"}},
        "explanation": "Marking the $66,800 support level so you can see how price reacted at that zone."
      }},
      {{
        "action_type": "open_panel",
        "params": {{"target": "orderBook"}},
        "explanation": "Opening the order book — there's a $4.2M bid wall stacked at $66,850-66,900 that helped defend support."
      }}
    ],
    "summary": "BTC bounced off $66,800 with neutral RSI and a fresh MACD cross. Watch the $66,800 support on any retest; if it holds, target is the $68,500 resistance."
  }}
}}
```

### Example 2: "Show me the order book for ETH"
Even though the synthesis may say "I cannot access real-time data", the chart actions can OPEN the order book panel directly via the UI. Plan a tour.
```json
{{
  "tour_plan": {{
    "title": "ETH order book walkthrough",
    "steps": [
      {{
        "action_type": "set_symbol",
        "params": {{"symbol": "ETHUSDT"}},
        "explanation": "Switching the chart to ETH so the order book shows the right market."
      }},
      {{
        "action_type": "highlight_candles",
        "params": {{"from_index": -10, "to_index": -1, "label": "Last 10 candles"}},
        "explanation": "Looking at the last few candles to see where price is right now — the order book shows liquidity at the current price level."
      }},
      {{
        "action_type": "open_panel",
        "params": {{"target": "orderBook"}},
        "explanation": "Opening the live order book so you can see bids stacked below current price and asks above — this is where traders are placing orders."
      }}
    ],
    "summary": "The order book is now visible for ETH. Watch the depth near the current price for large bids (support) or asks (resistance)."
  }}
}}
```

### Example 3: "Compare ETH and SOL on 4H"
```json
{{
  "tour_plan": {{
    "title": "ETH vs SOL: 4H relative strength",
    "steps": [
      {{
        "action_type": "add_indicator",
        "params": {{"indicator": "ema50"}},
        "explanation": "Adding the 50 EMA so we can compare both assets' trend posture on the same indicator."
      }},
      {{
        "action_type": "set_symbol",
        "params": {{"symbol": "ETHUSDT"}},
        "explanation": "Switching to ETH first — it's holding above the 50 EMA while SOL is testing it."
      }},
      {{
        "action_type": "create_annotation",
        "params": {{"time": 1719000000000, "price": 3520, "text": "ETH 50 EMA support"}},
        "explanation": "ETH's 50 EMA at $3,520 has held for 3 days — this is the trend line to watch."
      }},
      {{
        "action_type": "set_symbol",
        "params": {{"symbol": "SOLUSDT"}},
        "explanation": "Now SOL — it's right at the 50 EMA at $148. The bounce or break here will tell us if ETH keeps leading."
      }}
    ],
    "summary": "ETH is leading SOL with a 2.1% ETH/BTC gain in 24h. Both above 50 EMA but SOL is at the line; watch whether it holds for continued ETH strength."
  }}
}}
```

{action_types}
"""


async def plan_tour(
    user_query: str,
    expert_outputs: Dict[str, Any],
    synthesized_response: str,
    chart_context: Optional[Dict[str, Any]],
    mode: str,
) -> Optional[TourPlan]:
    """Plan a guided analysis tour from pipeline outputs.

    For "how to use LMView" type questions, returns a predefined workspace
    tour instead of calling the LLM. For market analysis queries, calls the
    LLM to generate a custom tour plan.
    """
    if mode != "interact":
        return None

    # Check for LMView workspace tour triggers
    if _is_lmview_tour_query(user_query):
        logger.info("Returning predefined LMView workspace tour.")
        return _build_workspace_tour()

    start_ms = time.monotonic_ns() // 1_000_000

    # Build context for the LLM
    context = _build_tour_context(user_query, expert_outputs, synthesized_response, chart_context)

    # Call LLM to plan the tour
    tour_plan_data = await _llm_plan_tour(context)

    if tour_plan_data is None:
        # LLM refused to plan a tour. Try a deterministic intent-based
        # fallback so simple queries like "show me the order book" or
        # "analyze BTC" still get a useful visual walkthrough. The
        # LLM is sometimes overcautious ("I can't access real-time
        # data") when in fact the chart actions dispatch directly
        # to the UI and don't need LLM data access.
        tour_plan_data = _intent_fallback_tour(user_query, chart_context)
        if tour_plan_data is None:
            logger.info("Tour planner returned null and no intent fallback matched — no tour created.")
            return None

    elapsed_ms = (time.monotonic_ns() // 1_000_000) - start_ms
    logger.info("Tour planned in %dms: %s (%d steps)", elapsed_ms, tour_plan_data.get("title", "?"), len(tour_plan_data.get("steps", [])))

    symbol = (chart_context or {}).get("symbol")
    timeframe = (chart_context or {}).get("timeframe")

    steps = []
    for step_data in tour_plan_data.get("steps", []):
        action_type = step_data.get("action_type", "")
        if action_type not in SUPPORTED_ACTIONS:
            logger.warning("Tour planner proposed unsupported action_type: %s", action_type)
            continue
        steps.append(TourStepAction(
            action_type=action_type,
            params=step_data.get("params", {}),
            explanation=step_data.get("explanation", ""),
            target_selector=step_data.get("target_selector"),
            requires_approval=step_data.get("requires_approval", False),
        ))

    if not steps:
        logger.warning("Tour planner produced 0 valid steps.")
        return None

    # Augment with deterministic visual steps derived from the chart
    # context: highlight the latest candle, mark key support/resistance
    # levels as annotations, and reveal any indicator the user already
    # has selected but isn't visible. This guarantees the tour has
    # something visually rich even if the LLM gave a sparse plan.
    steps = _augment_tour_with_visual_steps(
        steps=steps,
        expert_outputs=expert_outputs,
        chart_context=chart_context,
        synthesized_response=synthesized_response,
    )

    if not steps:
        logger.warning("Tour has 0 steps after augmentation.")
        return None

    # Collapse runs of identical action_type and cap at 6 steps.
    # Two back-to-back "Add indicator" or "Highlight" steps is noise
    # — the user only sees the last one anyway.
    steps = _dedupe_consecutive_steps(steps)
    steps = _cap_steps(steps, max_steps=6)

    if not steps:
        logger.warning("Tour has 0 steps after dedup/cap.")
        return None

    # Generate a stable tour_id from hash of content
    tour_id = f"ai-tour-{int(time.time())}"

    return TourPlan(
        tour_id=tour_id,
        title=tour_plan_data.get("title", "Guided Analysis"),
        steps=steps,
        summary=tour_plan_data.get("summary", synthesized_response[:500]),
        chart_snapshot={
            "symbol": symbol,
            "timeframe": timeframe,
        } if symbol or timeframe else None,
    )


def _augment_tour_with_visual_steps(
    steps: List["TourStepAction"],
    expert_outputs: Dict[str, Any],
    chart_context: Optional[Dict[str, Any]],
    synthesized_response: str,
) -> List["TourStepAction"]:
    """Append deterministic visual steps derived from chart context.

    The LLM's plan may focus on narrative analysis without picking out
    specific candles. This helper extracts numeric evidence from the
    expert outputs (support / resistance prices, key candle timestamps)
    and adds them as visual steps so the tour always has concrete
    annotations and highlights.

    Steps are only appended if their action is not already covered.
    """
    if not chart_context:
        return steps

    existing_actions = {s.action_type for s in steps}
    augmented: List["TourStepAction"] = list(steps)

    latest = chart_context.get("latest_candle") or {}
    recent = chart_context.get("recent_candles") or []

    # 1. Highlight the latest candle area so the user sees where price is
    #    right now.
    if "highlight_candles" not in existing_actions and recent:
        last_idx = len(recent) - 1
        augmented.append(TourStepAction(
            action_type="highlight_candles",
            params={
                "from_index": max(0, last_idx - 2),
                "to_index": last_idx,
                "label": "Latest action",
                "message": "Here is the most recent price action.",
            },
            explanation="Let's start by looking at the latest price action on the chart.",
        ))

    # 2. Add any visible indicators that the user has selected but the
    #    LLM didn't explicitly enable. Ensures the tour visually reflects
    #    the user's current chart setup. We add AT MOST one so we
    #    don't create a run of "Add indicator" steps.
    selected = chart_context.get("selected_indicators") or []
    already_added = any(
        s.action_type == "add_indicator" for s in steps
    )
    if selected and not already_added:
        augmented.append(TourStepAction(
            action_type="add_indicator",
            params={"indicator": str(selected[0])},
            explanation=f"Revealing the {selected[0]} indicator so we can read its signal.",
        ))

    # 3. Pull support / resistance prices from expert outputs and create
    #    annotations on the chart for the closest ones.
    sr_prices: List[Dict[str, Any]] = []
    for expert_name, output in expert_outputs.items():
        if not isinstance(output, dict):
            continue
        content = str(output.get("content") or output.get("text") or "")
        # Cheap regex-ish parsing for $price mentions within reason
        for marker in ("support", "resistance"):
            idx = content.lower().find(marker)
            while idx != -1:
                window = content[idx: idx + 200]
                m = re.search(r"\$?([0-9]{2,9}(?:\.[0-9]+)?)", window)
                if m:
                    sr_prices.append({
                        "type": marker,
                        "price": float(m.group(1)),
                        "source": expert_name,
                    })
                idx = content.lower().find(marker, idx + 1)
        # Stop after first 4 SR mentions to keep tours tight.
        if len(sr_prices) >= 4:
            break

    if sr_prices and "create_annotation" not in existing_actions:
        # Dedupe by (type, rounded price)
        seen = set()
        uniq: List[Dict[str, Any]] = []
        for p in sr_prices:
            key = (p["type"], round(p["price"], 2))
            if key in seen:
                continue
            seen.add(key)
            uniq.append(p)
        for p in uniq[:2]:
            augmented.append(TourStepAction(
                action_type="create_annotation",
                params={
                    "time": int(time.time() * 1000),
                    "price": p["price"],
                    "text": f"{p['type'].title()} ~ ${p['price']:.2f}",
                },
                explanation=f"Marking the key {p['type']} level around ${p['price']:.2f} on the chart.",
            ))

    # 4. If the analysis talks about order flow / liquidity / large bids,
    #    open the order book panel so the user sees the depth.
    synth = (synthesized_response or "").lower()
    needs_orderbook = any(
        token in synth for token in (
            "order book", "orderbook", "liquidity", "bid", "ask spread",
            "depth", "large bid", "large ask", "order flow", "sell wall",
            "buy wall",
        )
    )
    if needs_orderbook and "open_panel" not in existing_actions and "switch_panel_tab" not in existing_actions:
        augmented.append(TourStepAction(
            action_type="open_panel",
            params={
                "target": "orderBook",
                "label": "Order Book",
                "message": "Live liquidity near the current price.",
            },
            explanation="Opening the order book so you can see live liquidity around the current price.",
        ))

    # 5. If the analysis mentions multiple timeframes ("higher timeframes",
    #    "4h trend", "weekly chart"), add a set_timeframe step so the user
    #    can see the broader context.
    needs_multi_tf = any(
        token in synth for token in (
            "higher timeframe", "lower timeframe", "4h trend", "daily trend",
            "weekly", "multi-timeframe", "higher time frame", "broader trend",
        )
    )
    if needs_multi_tf and "set_timeframe" not in existing_actions:
        # Default to 4h — a common higher-timeframe view
        augmented.append(TourStepAction(
            action_type="set_timeframe",
            params={"timeframe": "4h"},
            explanation="Stepping back to a higher timeframe (4h) to confirm the broader trend.",
        ))

    # 6. If the analysis talks about a different market than the one on
    #    screen, switch to it.
    market_match = re.search(
        r"\b(ETH|SOL|BNB|XRP|DOGE|ADA|AVAX|LTC|LINK|MATIC|DOT)[\s/]?(USDT|USDC)?\b",
        synth,
    )
    if market_match and "set_symbol" not in existing_actions:
        token = market_match.group(1).upper()
        quote = market_match.group(2) or "USDT"
        new_symbol = f"{token}{quote}"
        current = (chart_context or {}).get("symbol", "")
        if new_symbol != current:
            augmented.append(TourStepAction(
                action_type="set_symbol",
                params={"symbol": new_symbol},
                explanation=f"Switching to {new_symbol} so you can compare the setup there.",
            ))

    # 7. If the analysis mentions news / markets overview / a wider view,
    #    briefly visit the markets/news tab.
    needs_markets_view = any(
        token in synth for token in (
            "market overview", "news", "headlines", "broader market",
            "sector", "narrative", "macro", "sentiment",
        )
    )
    if needs_markets_view and "switch_app_view" not in existing_actions:
        augmented.append(TourStepAction(
            action_type="switch_app_view",
            params={
                "view": "marketsNews",
                "label": "Markets & News",
                "message": "Broader market context for this setup.",
            },
            explanation="Popping over to Markets & News for the broader context on this move.",
        ))

    return augmented


def _build_tour_context(
    user_query: str,
    expert_outputs: Dict[str, Any],
    synthesized_response: str,
    chart_context: Optional[Dict[str, Any]],
) -> str:
    """Build a condensed context string for the tour planner LLM."""
    parts = [f"## User Query\n{user_query}\n"]

    if chart_context:
        ctx = chart_context
        chart_info = f"## Chart Context\nSymbol: {ctx.get('symbol', '?')} | Timeframe: {ctx.get('timeframe', '?')}"
        if ctx.get("selected_indicators"):
            chart_info += f"\nIndicators active: {', '.join(ctx['selected_indicators'])}"
        parts.append(chart_info)

    # Include key data from experts
    for expert_name, output in expert_outputs.items():
        if isinstance(output, dict):
            content = output.get("content", "") or output.get("text", "")
            if content and len(str(content)) > 20:
                parts.append(f"## {expert_name.title()}\n{str(content)[:1000]}")

    # Include the final synthesis
    if synthesized_response:
        parts.append(f"## Analysis Summary\n{synthesized_response[:2000]}")

    return "\n\n".join(parts)


async def _llm_plan_tour(context: str) -> Optional[Dict[str, Any]]:
    """Call the LLM to generate a tour plan from context."""
    try:
        from ai_service.providers.router import get_provider_router
        from backend.models.ai.providers import LLMCompletionRequest

        router = get_provider_router()
        request = LLMCompletionRequest(
            messages=[
                {"role": "system", "content": TOUR_PLANNER_SYSTEM_PROMPT.format(
                    action_types=", ".join(SUPPORTED_ACTIONS),
                    action_params=_action_params_doc(),
                )},
                {"role": "user", "content": context},
            ],
            temperature=0.3,
            max_tokens=2000,
        )

        # ``route_completion`` returns ``(LLMCompletionResponse, ProviderRoutingResult)``
        response, _routing = await router.route_completion(request)

        content = (response.content or "").strip()
        if not content:
            logger.warning("Tour planner LLM returned empty response.")
            return None

        # Parse JSON from response (may have markdown fences)
        parsed = _parse_json_response(content)
        if parsed is None:
            logger.warning("Tour planner LLM returned invalid JSON: %.200s", content)
            return None

        return parsed.get("tour_plan")

    except Exception as exc:
        logger.error("Tour planner LLM call failed: %s", exc)
        return None


def _parse_json_response(content: str) -> Optional[Dict[str, Any]]:
    """Parse JSON from LLM response, handling markdown fences."""
    # Try direct parse first
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code fences
    for marker in ["```json", "```"]:
        if marker in content:
            start = content.index(marker) + len(marker)
            end = content.index("```", start) if "```" in content[start:] else len(content)
            candidate = content[start:end].strip()
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue

    return None


def _action_params_doc() -> str:
    """Concise reference of every supported action_type and its params.
    Kept separate from the system prompt so the prompt itself can stay
    readable while the parameter reference stays close to the SUPPORTED_ACTIONS
    list above (single source of truth)."""
    return (
        "- highlight_section: dim everything except a UI section. params: {target, label?, message?}\n"
        "- view_section: open and highlight a section. params: {target}\n"
        "- highlight_chart_area: highlight a rect. params: {left_pct, top_pct, width_pct, height_pct, label?, message?}\n"
        "- highlight_candles: highlight candle range. params: {from_index?, to_index?, start_time?, end_time?, label?, message?}\n"
        "- add_indicator: show an indicator. params: {indicator: rsi|macd|bb|sma20|sma50|ema12|ema26|ema50|vwap|volume|volumeMa|stochastic|mfi|atr|ichimoku|supertrend|psar|support_resistance}\n"
        "- remove_indicator: hide an indicator. params: {indicator}\n"
        "- configure_indicator: update settings. params: {indicator, settings: {period?, color?}}\n"
        "- draw_tool / draw_trendline: draw on chart. params: {tool, points: [{time, price}], text?, color?, lineWidth?}\n"
        "- create_annotation: text label. params: {time (epoch_ms), price, text}\n"
        "- clear_drawings: remove all AI drawings. params: {}\n"
        "- delete_drawing: remove one. params: {drawing_id}\n"
        "- set_drawing_color: recolor. params: {drawing_id, color}\n"
        "- set_timeframe: params: {timeframe: 1s|1m|3m|5m|15m|30m|1h|2h|4h|6h|12h|1d|3d|1w|1M}\n"
        "- set_chart_type: params: {chart_type: candles|line|area|bar|heikinAshi|renko|lineBreak|kagi|pointFigure|hollowCandles|baseline|columns}\n"
        "- set_symbol: change market. params: {symbol: e.g. BTCUSDT}\n"
        "- zoom_chart: params: {direction: in|out, anchor_ratio?: 0..1, steps?: int}\n"
        "- scroll_chart: params: {target: start|end|left|right, bars?: int}\n"
        "- scroll_chart_to_time: params: {time: epoch_sec_or_ms}\n"
        "- reset_chart_view: params: {}\n"
        "- open_panel: open right panel. params: {target: overview|watchlist|orderBook|recentTrades|ai, label?, message?}\n"
        "- close_panel: params: {}\n"
        "- switch_panel_tab: params: {tab: watchlist|orderBook|recentTrades}\n"
        "- switch_app_view: params: {view: charts|marketsNews|screener}\n"
        "- open_settings / close_settings: params: {}\n"
        "- fetch_historical_prices: load historical candles. params: {symbol, timeframe, start_ms, end_ms, limit?}\n"
        "- end_tour: cancel the active tour. params: {}\n"
    )


def _dedupe_consecutive_steps(steps: List[TourStepAction]) -> List[TourStepAction]:
    """Drop runs of the same action_type.

    Two back-to-back "add_indicator" steps is just noise; collapse to
    one. Also collapse two back-to-back highlight_* steps because the
    user only sees the last one anyway. We keep the FIRST step of the
    run so its explanation is the one the user reads.
    """
    if not steps:
        return steps
    deduped: List[TourStepAction] = [steps[0]]
    for s in steps[1:]:
        if s.action_type == deduped[-1].action_type:
            continue
        deduped.append(s)
    return deduped


def _cap_steps(steps: List[TourStepAction], max_steps: int = 6) -> List[TourStepAction]:
    """Cap the tour to max_steps to keep tours tight."""
    return steps[:max_steps]


# Symbols we recognise for intent-based fallback. Match the user query
# with a regex so we can pick the right chart action without going
# through the LLM.
_SYMBOL_PATTERNS = [
    ("BTC", ["btc", "bitcoin"]),
    ("ETH", ["eth", "ethereum"]),
    ("SOL", ["sol", "solana"]),
    ("BNB", ["bnb"]),
    ("XRP", ["xrp", "ripple"]),
    ("DOGE", ["doge", "dogecoin"]),
    ("ADA", ["ada", "cardano"]),
    ("AVAX", ["avax", "avalanche"]),
    ("LINK", ["link", "chainlink"]),
    ("DOT", ["dot", "polkadot"]),
    ("MATIC", ["matic", "polygon"]),
]


def _extract_symbol_from_query(query: str, default: str = "BTCUSDT") -> str:
    """Return the most likely symbol mentioned in a query, or default."""
    lowered = query.lower()
    for symbol, patterns in _SYMBOL_PATTERNS:
        for p in patterns:
            if p in lowered:
                return f"{symbol}USDT"
    return default


def _intent_fallback_tour(
    user_query: str,
    chart_context: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Deterministic tour plan based on the user's intent keywords.

    The LLM sometimes refuses to plan a tour (e.g. "I cannot access
    real-time order book data") even though the chart actions
    dispatch directly to the UI and don't need LLM data access. This
    fallback recognises common intents and returns a useful tour
    without the LLM.
    """
    lowered = user_query.lower().strip()
    if not lowered:
        return None

    current_symbol = (chart_context or {}).get("symbol", "BTCUSDT")
    target_symbol = _extract_symbol_from_query(user_query, current_symbol)
    want_symbol_switch = target_symbol != current_symbol

    steps: List[Dict[str, Any]] = []
    title = None

    # Order book intent
    if any(tok in lowered for tok in ("order book", "orderbook", "depth", "liquidity", "bids", "asks")):
        title = f"{target_symbol} order book walkthrough"
        if want_symbol_switch:
            steps.append({
                "action_type": "set_symbol",
                "params": {"symbol": target_symbol},
                "explanation": f"Switching the chart to {target_symbol} so the order book shows the right market.",
            })
        steps.append({
            "action_type": "highlight_candles",
            "params": {"from_index": -10, "to_index": -1, "label": "Last 10 candles"},
            "explanation": "Looking at the most recent candles so you can see where price is right now — the order book shows liquidity at the current price level.",
        })
        steps.append({
            "action_type": "open_panel",
            "params": {"target": "orderBook"},
            "explanation": "Opening the live order book so you can see bids stacked below current price and asks above — this is where traders are placing orders.",
        })

    # Compare intent
    elif any(tok in lowered for tok in ("compare", "vs", "versus", "against", "between")):
        symbols = []
        for sym, patterns in _SYMBOL_PATTERNS:
            if any(p in lowered for p in patterns):
                symbols.append(f"{sym}USDT")
        if len(symbols) >= 2:
            title = f"Compare {symbols[0].replace('USDT', '')} vs {symbols[1].replace('USDT', '')}"
            steps.append({
                "action_type": "add_indicator",
                "params": {"indicator": "ema50"},
                "explanation": "Adding the 50 EMA so we can compare both assets' trend posture on the same indicator.",
            })
            for sym in symbols[:2]:
                steps.append({
                    "action_type": "set_symbol",
                    "params": {"symbol": sym},
                    "explanation": f"Switching to {sym} so you can see its setup on the chart.",
                })
                steps.append({
                    "action_type": "highlight_candles",
                    "params": {"from_index": -20, "to_index": -1, "label": f"{sym} recent action"},
                    "explanation": f"Last 20 candles of {sym} action for trend context.",
                })

    # News / market overview intent
    elif any(tok in lowered for tok in ("news", "headlines", "market overview", "broader market", "macro")):
        title = "News & market overview"
        steps.append({
            "action_type": "highlight_candles",
            "params": {"from_index": -10, "to_index": -1, "label": "Recent action"},
            "explanation": "Current price action on the chart, then we'll pop over to the news feed for context.",
        })
        steps.append({
            "action_type": "switch_app_view",
            "params": {"view": "marketsNews"},
            "explanation": "Opening the Markets & News view for the latest headlines and broader market context.",
        })

    # Analyze intent
    elif any(tok in lowered for tok in ("analyze", "analysis", "review", "what do you see", "thoughts on", "look at")):
        title = f"{target_symbol} analysis"
        if want_symbol_switch:
            steps.append({
                "action_type": "set_symbol",
                "params": {"symbol": target_symbol},
                "explanation": f"Switching to {target_symbol} for this analysis.",
            })
        steps.append({
            "action_type": "highlight_candles",
            "params": {"from_index": -20, "to_index": -1, "label": "Recent action"},
            "explanation": f"Last 20 candles of {target_symbol} action — this is the setup we're analyzing.",
        })
        steps.append({
            "action_type": "add_indicator",
            "params": {"indicator": "rsi"},
            "explanation": "RSI shows momentum. Watch for overbought (>70) or oversold (<30) zones — divergences between RSI and price often signal reversals.",
        })
        steps.append({
            "action_type": "open_panel",
            "params": {"target": "orderBook"},
            "explanation": "Opening the order book so you can see live liquidity near the current price — large bid/ask walls often mark support/resistance.",
        })

    # Indicator tutorial intent
    elif any(tok in lowered for tok in ("rsi", "macd", "bollinger", "indicator", "moving average", "sma", "ema")):
        title = "Technical indicators"
        if "rsi" in lowered:
            steps.append({
                "action_type": "add_indicator",
                "params": {"indicator": "rsi"},
                "explanation": "RSI (Relative Strength Index) measures momentum on a 0-100 scale. >70 = overbought, <30 = oversold.",
            })
        if "macd" in lowered:
            steps.append({
                "action_type": "add_indicator",
                "params": {"indicator": "macd"},
                "explanation": "MACD shows momentum direction (line) and strength (histogram). Crosses above the signal line are bullish.",
            })
        if "bollinger" in lowered or "bb" in lowered:
            steps.append({
                "action_type": "add_indicator",
                "params": {"indicator": "bb"},
                "explanation": "Bollinger Bands: price touching the upper band = overbought, lower band = oversold. Squeezes often precede big moves.",
            })
        if "ema" in lowered or "sma" in lowered or "moving average" in lowered:
            steps.append({
                "action_type": "add_indicator",
                "params": {"indicator": "sma20"},
                "explanation": "SMA 20 (20-period simple moving average) smooths out price. Price above = bullish trend, below = bearish.",
            })

    if not steps or title is None:
        return None

    return {
        "title": title,
        "steps": steps,
        "summary": f"Walkthrough of {title} — review the steps above for the key signals.",
    }


def _is_lmview_tour_query(query: str) -> bool:
    """Detect user asks for LMView walkthrough.

    The Interact-mode walkthrough is the primary entry point when the
    user asks how to use LMView, what's in the workspace, or asks for a
    demo / guide / tour / overview. We also match "learn lmview" /
    "show me around" / "walk me through". The match is intentionally
    permissive because the predefined template is the right answer for
    *any* high-level "what is this app" question.
    """
    lowered = query.lower()
    triggers = [
        "tour", "guide", "demo", "walkthrough", "walk-through",
        "tutorial", "show me around", "show me how",
        "learn lmview", "learn this", "teach me",
        "how to use lmview", "how to use this",
        "how do i use", "where do i start",
        "what is lmview", "what can i do", "what can lmview",
        "lmview features", "lmview overview", "overview of lmview",
        "what's in lmview", "what is in lmview",
        "guide me", "give me a tour", "take me through",
    ]
    return any(tok in lowered for tok in triggers)


def _build_workspace_tour() -> Optional[TourPlan]:
    """Construct TourPlan from predefined WORKSPACE_OVERVIEW_TOUR.

    Maps TourTemplate steps to TourStepAction objects expected by frontend.
    Filters out any step whose action_type is not in SUPPORTED_ACTIONS so a
    stale template cannot re-freeze the chart with broken steps. The LLM
    workflow should be picked up by name from SUPPORTED_ACTIONS; this
    function does *not* invent aliases like ``manage_indicator``.
    """
    template = WORKSPACE_OVERVIEW_TOUR
    steps = []
    for s in template.steps:
        action_name = s.action.get("name", "")
        if action_name not in SUPPORTED_ACTIONS:
            logger.warning(
                "Skipping LMView workspace tour step with unsupported action %r",
                action_name,
            )
            continue
        steps.append(TourStepAction(
            action_type=action_name,
            params=s.action.get("arguments", {}),
            explanation=s.explanation,
            target_selector=s.target_selector,
            requires_approval=s.requires_approval,
        ))
    if not steps:
        logger.warning("LMView workspace tour produced 0 valid steps.")
        return None
    return TourPlan(
        tour_id=template.tour_id,
        title=template.title,
        steps=steps,
        summary=template.description,
        chart_snapshot=None,
    )
