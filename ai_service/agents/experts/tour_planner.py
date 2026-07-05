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
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from backend.models.ai.tour import GuidedAction, TourPlan, WalkthroughStep
from ai_service.tours.tour_templates import (
    WORKSPACE_OVERVIEW_TOUR,
    INDICATOR_TUTORIAL_TOUR,
)

logger = logging.getLogger("ai_service.agents.experts.tour_planner")


@dataclass
class PlannedStep:
    """Internal flat tour step before conversion to TourPlan schema."""
    action_type: str
    params: Dict[str, Any]
    explanation: str
    target_selector: Optional[str] = None
    requires_approval: bool = False


def _guided_action_from_step(step: PlannedStep) -> GuidedAction:
    """Convert internal flat step to current frontend action schema."""
    action_type = step.action_type
    params = dict(step.params or {})

    if action_type == "draw_horizontal_line":
        action_type = "draw_tool"
        params.setdefault("tool", "horizontal")
    elif action_type == "draw_fib":
        action_type = "draw_tool"
        params.setdefault("tool", "fibonacci")
    elif action_type == "draw_rectangle":
        action_type = "draw_tool"
        params.setdefault("tool", "rectangle")

    return GuidedAction(
        type=action_type,
        params=params,
        requires_approval=step.requires_approval,
    )


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
    "draw_horizontal_line",     # support / resistance horizontal line
    "draw_fib",                 # Fibonacci retracement overlay
    "draw_rectangle",           # highlight a price/time box
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



def _extract_analysis_data(synthesized_response: str) -> Dict[str, Any]:
    """Parse synthesis output for key analytical data points.

    Returns structured dict with:
      - trend: overall trend direction (bullish/bearish/neutral)
      - price_current: current price if mentioned
      - indicators: dict of indicator name → value
      - support_levels: list of support prices mentioned
      - resistance_levels: list of resistance prices mentioned
      - patterns: list of patterns mentioned
      - conclusion: the last substantive paragraph (for recap)
      - key_findings: list of short analytical findings
    """
    data: Dict[str, Any] = {
        "trend": "neutral",
        "price_current": None,
        "indicators": {},
        "support_levels": [],
        "resistance_levels": [],
        "patterns": [],
        "conclusion": "",
        "key_findings": [],
    }
    if not synthesized_response:
        return data

    text = synthesized_response

    # ── Trend direction ──
    first_200 = text[:200].lower()
    bullish_words = ["bullish", "uptrend", "upward", "rising", "breakout", "buy", "long"]
    bearish_words = ["bearish", "downtrend", "downward", "falling", "breakdown", "sell", "short"]
    bullish_score = sum(1 for w in bullish_words if w in first_200)
    bearish_score = sum(1 for w in bearish_words if w in first_200)
    if bullish_score > bearish_score:
        data["trend"] = "bullish"
    elif bearish_score > bullish_score:
        data["trend"] = "bearish"

    # ── Current price ──
    # Look for price near words like "price", "trading at", "currently"
    # Use price-specific context words — avoid "at" alone (matches "RSI at 28.3")
    price_context = re.search(
        r"(?:(?:current|spot|trading)\s+price|price\s+is|trading\s+(?:at|near|around)|currently\s+(?:at|trading)|at\s+\*{0,2}\$)\s*\*{0,2}\$?([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?)",
        text, re.IGNORECASE
    )
    if price_context:
        try:
            data["price_current"] = float(price_context.group(1).replace(",", ""))
        except (ValueError, TypeError):
            pass

    # ── Indicator values ──
    # Patterns like "RSI at 28.3", "RSI: 28.3", "MACD: -45.2"
    # Also handles markdown ** and label-value separation:
    #   "**RSI** is at **28.3**" → 28.3
    #   "- RSI: 28.3" → 28.3
    # Uses .*? to skip any text between indicator name and value.
    indicator_patterns = [
        ("rsi", r"(?:RSI|rsi)\s*(?::|is|at|=|≈)?[^.]*?(?:\*{0,2})([0-9]+\.?[0-9]*)(?:\*{0,2})"),
        ("macd", r"(?:MACD|macd)\s*(?::|is|at|=|≈)?[^.]*?(?:\*{0,2})(-?[0-9]+\.?[0-9]*)(?:\*{0,2})"),
        ("bb_upper", r"(?:upper\s*Bollinger|BB\s*upper)\s*(?::|is|at|=|≈)?[^.]*?\$?(?:\*{0,2})([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)(?:\*{0,2})"),
        ("bb_lower", r"(?:lower\s*Bollinger|BB\s*lower)\s*(?::|is|at|=|≈)?[^.]*?\$?(?:\*{0,2})([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)(?:\*{0,2})"),
        ("ema50", r"(?:50\s*EMA|EMA\s*50|ema50)\s*(?::|is|at|=|≈)?[^.]*?\$?(?:\*{0,2})([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)(?:\*{0,2})"),
        ("sma20", r"(?:20\s*(?:SMA|MA|sma)|SMA\s*20|sma20)\s*(?::|is|at|=|≈)?[^.]*?\$?(?:\*{0,2})([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)(?:\*{0,2})"),
        ("volume", r"(?:volume|vol\.?)\s*(?::|is|at|=|≈)?[^.]*?([0-9]+(?:\.[0-9]+)?[KMB]?)"),
    ]
    for name, pattern in indicator_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                val_str = m.group(1).strip()
                if val_str.endswith("K"):
                    data["indicators"][name] = float(val_str[:-1]) * 1000
                elif val_str.endswith("M"):
                    data["indicators"][name] = float(val_str[:-1]) * 1_000_000
                elif val_str.endswith("B"):
                    data["indicators"][name] = float(val_str[:-1]) * 1_000_000_000
                else:
                    data["indicators"][name] = float(val_str.replace(",", ""))
            except (ValueError, TypeError):
                pass

    # ── Support / Resistance levels ──
    # Find numbers near "support" or "resistance" words
    for label, key in [("support", "support_levels"), ("resistance", "resistance_levels")]:
        pat = label + "\\s*(?::|at|≈|around|near|level)?\\s*(?:\\*\\*)?\\$?([0-9,]+(?:\\.[0-9]+)?)(?:\\*\\*)?"
        for m in re.finditer(pat, text, re.IGNORECASE):
            try:
                val = float(m.group(1).replace(",", ""))
                if val not in data[key]:
                    data[key].append(val)
            except (ValueError, TypeError):
                pass

    # ── Patterns ──
    pattern_names = [
        "double top", "double bottom", "head and shoulders", "inverse head and shoulders",
        "ascending triangle", "descending triangle", "symmetrical triangle",
        "bull flag", "bear flag", "pennant", "wedge",
        "engulfing", "doji", "hammer", "shooting star", "morning star", "evening star",
        "three white soldiers", "three black crows",
    ]
    found_patterns = []
    for p in pattern_names:
        if p in text.lower():
            found_patterns.append(p.title())
    data["patterns"] = found_patterns[:3]

    # ── Key findings ──
    # Look for bullet points with analytical content. Clean markdown.
    bullet_pattern = re.findall(r"[-*]\s*(?:[A-Z].*?)(?:\.|$)", text, re.MULTILINE)
    for bp in bullet_pattern:
        cleaned = bp.strip("-* ").strip()
        # Strip markdown formatting
        cleaned = cleaned.replace("**", "").replace("__", "").replace("*", "").strip()
        # Skip if it's a header, too short, or looks like a table cell
        if cleaned.startswith("#") or len(cleaned) < 15:
            continue
        if cleaned.startswith("[") or "|" in cleaned:
            continue
        if cleaned not in data["key_findings"]:
            data["key_findings"].append(cleaned)
    data["key_findings"] = data["key_findings"][:5]

    # ── Conclusion (last substantive paragraph) ──
    # Split on double newlines, skip headers/blockquotes/short paras
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    for para in reversed(paragraphs):
        if len(para) < 80:
            continue
        if para.startswith("#") or para.startswith("---") or para.startswith(">"):
            continue
        # Clean markdown
        cleaned_para = para.replace("**", "").replace("__", "").strip()
        if len(cleaned_para) >= 80:
            data["conclusion"] = cleaned_para
            break

    return data


async def plan_tour(
    user_query: str,
    expert_outputs: Dict[str, Any],
    synthesized_response: str,
    chart_context: Optional[Dict[str, Any]],
    mode: str,
) -> Optional[TourPlan]:
    """Plan a guided analysis tour from pipeline outputs.

    Primary path: deterministic intent-based fallback (covers 80%+ of cases).
    No LLM call — uses keyword matching against the user query to build
    a structured tour plan. Augmented with visual steps from expert data
    (support/resistance levels, indicator values, candle highlights).

    Each step's explanation is now enriched with actual analytical findings
    from the synthesized response — not generic boilerplate. The tour recap
    uses the analysis conclusion as its summary text.
    """
    if mode != "interact":
        return None

    # Check for LMView workspace tour triggers
    if _is_lmview_tour_query(user_query):
        logger.info("Returning predefined LMView workspace tour.")
        return _build_workspace_tour()

    start_ms = time.monotonic_ns() // 1_000_000

    # Extract analysis data from the synthesis output
    analysis_data = _extract_analysis_data(synthesized_response)

    # Deterministic intent-based fallback — primary path, no LLM call
    tour_plan_data = _intent_fallback_tour(
        user_query, chart_context, analysis_data
    )

    if tour_plan_data is None:
        logger.info("No deterministic tour matched for query — no tour created.")
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
        steps.append(PlannedStep(
            action_type=action_type,
            params=step_data.get("params", {}),
            explanation=step_data.get("explanation", ""),
            target_selector=step_data.get("target_selector"),
            requires_approval=step_data.get("requires_approval", False),
        ))

    if not steps:
        logger.warning("Tour planner produced 0 valid steps.")
        return None

    # Timeframe Alignment: If current chart timeframe is different from analysis timeframe,
    # prepend a set_timeframe step to ensure they align!
    ta_out = expert_outputs.get("technical_analysis", {})
    analysis_tf = None
    if isinstance(ta_out, dict):
        analysis_tf = ta_out.get("structured_data", {}).get("timeframe")

    if analysis_tf and timeframe and str(analysis_tf).lower() != str(timeframe).lower():
        has_set_tf = any(s.action_type == "set_timeframe" for s in steps)
        if not has_set_tf:
            steps.insert(0, PlannedStep(
                action_type="set_timeframe",
                params={"timeframe": analysis_tf},
                explanation=f"Switching chart to the {analysis_tf} timeframe to align with the technical indicators used in this analysis.",
            ))

    # Augment with deterministic visual steps derived from the chart
    # context: highlight the latest candle, mark key support/resistance
    # levels as annotations, and reveal any indicator the user already
    # has selected but isn't visible. This guarantees the tour has
    # something visually rich even if the deterministic plan was sparse.
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
    steps = _dedupe_consecutive_steps(steps)
    steps = _cap_steps(steps, max_steps=6)

    if not steps:
        logger.warning("Tour has 0 steps after dedup/cap.")
        return None

    tour_id = f"ai-tour-{int(time.time())}"

    # Build summary from analysis conclusion if available, otherwise fallback
    summary = analysis_data.get("conclusion", "")
    if not summary:
        summary = tour_plan_data.get("summary", synthesized_response[:500])

    walkthrough_steps = [
        WalkthroughStep(
            explanation=step.explanation,
            actions=[_guided_action_from_step(step)],
            keep_effects=True,
            chart_freeze=True,
        )
        for step in steps
    ]

    return TourPlan(
        tour_id=tour_id,
        title=tour_plan_data.get("title", "Guided Analysis"),
        steps=walkthrough_steps,
        summary=summary,
        chart_snapshot={
            "symbol": symbol,
            "timeframe": timeframe,
        } if symbol or timeframe else None,
    )


def _dedupe_consecutive_steps(steps: List[PlannedStep]) -> List[PlannedStep]:
    """Drop runs of the same action_type.

    Two back-to-back "add_indicator" steps is just noise; collapse to
    one. Also collapse two back-to-back highlight_* steps because the
    user only sees the last one anyway. We keep the FIRST step of the
    run so its explanation is the one the user reads.
    """
    if not steps:
        return steps
    deduped: List[PlannedStep] = [steps[0]]
    for s in steps[1:]:
        # Collapse consecutive same action_type UNLESS they are
        # draw_horizontal_line with different labels (e.g. support vs resistance)
        if s.action_type == deduped[-1].action_type:
            if s.action_type == "draw_horizontal_line":
                # Keep both S&R lines when labels differ
                label_a = deduped[-1].params.get("label", "")
                label_b = s.params.get("label", "")
                if label_a != label_b:
                    deduped.append(s)
                    continue
            continue
        deduped.append(s)
    return deduped


def _cap_steps(steps: List[PlannedStep], max_steps: int = 6) -> List[PlannedStep]:
    """Cap the tour to max_steps to keep tours tight, preserving setup and concluding steps."""
    if len(steps) <= max_steps:
        return steps
    if max_steps <= 2:
        return [steps[0], steps[-1]] if max_steps == 2 else [steps[0]]

    first_step = steps[0]
    last_step = steps[-1]
    middle_steps = steps[1:-1]

    target_middle_count = max_steps - 2
    step_size = len(middle_steps) / target_middle_count

    sampled_middle = []
    for i in range(target_middle_count):
        idx = int(i * step_size)
        if idx < len(middle_steps):
            sampled_middle.append(middle_steps[idx])

    return [first_step] + sampled_middle + [last_step]


def _augment_tour_with_visual_steps(
    steps: List[PlannedStep],
    expert_outputs: Dict[str, Any],
    chart_context: Optional[Dict[str, Any]],
    synthesized_response: str,
) -> List[PlannedStep]:
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
    augmented: List[PlannedStep] = list(steps)

    latest = chart_context.get("latest_candle") or {}
    recent = chart_context.get("recent_candles") or []

    # 1. Highlight the latest candle area so the user sees where price is
    #    right now.
    if "highlight_candles" not in existing_actions and recent:
        last_idx = len(recent) - 1
        augmented.append(PlannedStep(
            action_type="highlight_candles",
            params={
                "from_index": max(0, last_idx - 2),
                "to_index": last_idx,
                "label": "Latest action",
                "message": "Here is the most recent price action.",
            },
            explanation="Let's start by looking at the latest price action on the chart.",
        ))

    # 2. Read structured technical analysis data for contextual highlights.
    #    If the TA expert detected specific signals (breakout, divergence,
    #    overbought/oversold), add a contextual zone highlight based on
    #    actual data — not just keyword matching on the response text.
    ta_output = expert_outputs.get("technical_analysis", {})
    if isinstance(ta_output, dict):
        structured = ta_output.get("structured_data", {}) or {}
        ta_signals = structured.get("signals", [])
        ta_summary = structured.get("trend_summary", "neutral")

        # Find the most interesting signal for a contextual zone highlight
        interesting_zones = {
            "oversold": ("reversal_candles", "bullish"),
            "overbought": ("reversal_candles", "bearish"),
            "bullish_crossover": ("trend_push", "bullish"),
            "bearish_crossover": ("trend_push", "bearish"),
            "high_volume": ("volume_spike", "neutral"),
        }
        for sig in ta_signals:
            sig_name = sig.get("signal", "")
            if sig_name in interesting_zones and "highlight_contextual_zone" not in existing_actions:
                zone_type, direction = interesting_zones[sig_name]
                indicator = sig.get("indicator", "")
                value = sig.get("value")
                label = f"{indicator} {sig_name.replace('_', ' ').title()}"
                message = f"{indicator} signals {sig_name.replace('_', ' ')} ({value:.1f})" if value is not None else f"{indicator} {sig_name.replace('_', ' ')}"
                augmented.append(PlannedStep(
                    action_type="highlight_contextual_zone",
                    params={
                        "zone_type": zone_type,
                        "label": label,
                        "message": message,
                        "direction": direction,
                        "candle_count": 8,
                    },
                    explanation=f"Highlighting the zone where {indicator} shows {sig_name.replace('_', ' ')}.",
                ))
                break

        # Check for candle patterns detected
        patterns = structured.get("patterns", [])
        if patterns and "highlight_contextual_zone" not in existing_actions:
            for p in patterns[:1]:
                pat_dir = p.get("direction", "neutral")
                augmented.append(PlannedStep(
                    action_type="highlight_contextual_zone",
                    params={
                        "zone_type": "reversal_candles" if "reversal" in str(pat_dir) else "recent_action",
                        "label": f"Pattern: {p.get('name', 'Candlestick')}",
                        "message": p.get("description", "Key candlestick pattern detected"),
                        "direction": pat_dir,
                        "candle_count": 4,
                    },
                    explanation=f"Calling out the {p.get('name', 'pattern')} candlestick pattern.",
                ))
                break

    # 3. Add any visible indicators that the user has selected but the
    #    LLM didn't explicitly enable. Ensures the tour visually reflects
    #    the user's current chart setup. We add AT MOST one so we
    #    don't create a run of "Add indicator" steps.
    selected = chart_context.get("selected_indicators") or []
    already_added = any(
        s.action_type == "add_indicator" for s in steps
    )
    if selected and not already_added:
        augmented.append(PlannedStep(
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
            augmented.append(PlannedStep(
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
        augmented.append(PlannedStep(
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
        augmented.append(PlannedStep(
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
            augmented.append(PlannedStep(
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
        augmented.append(PlannedStep(
            action_type="switch_app_view",
            params={
                "view": "marketsNews",
                "label": "Markets & News",
                "message": "Broader market context for this setup.",
            },
            explanation="Popping over to Markets & News for the broader context on this move.",
        ))

    return augmented

# Symbol pattern matching for intent-based tours
# Keys are ticker symbols, values are lists of keywords to match
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


def _fmt_explanation(base: str, analysis_data: Optional[Dict[str, Any]] = None) -> str:
    """Append analytical data to a step explanation.

    Transforms generic explanations like "RSI shows momentum" into
    "RSI shows momentum — RSI is currently at 28.3 (oversold)."
    """
    if not analysis_data:
        return base

    findings = analysis_data.get("key_findings", [])
    indicators = analysis_data.get("indicators", {})
    trend = analysis_data.get("trend", "neutral")
    price = analysis_data.get("price_current")
    supports = analysis_data.get("support_levels", [])
    resistances = analysis_data.get("resistance_levels", [])
    patterns = analysis_data.get("patterns", [])

    tail_parts = []
    lower_base = base.lower()

    # Price context — bold the value
    if price and ("price" in lower_base or "trend" in lower_base or "trading" in lower_base):
        price_str = f"**${price:,.2f}**" if price >= 1 else f"**${price:.6f}**"
        tail_parts.append(f"Price: {price_str}")

    # Trend direction — bold with emoji
    if "trend" in lower_base or "direction" in lower_base:
        emoji = "🟢" if trend == "bullish" else ("🔴" if trend == "bearish" else "⚪")
        tail_parts.append(f"Trend: **{emoji} {trend.upper()}**")

    # Indicator values matching the step context — bold the value
    ind_map = {
        "rsi": ["rsi"],
        "macd": ["macd", "momentum"],
        "bb_upper": ["bollinger", "bb", "band", "upper"],
        "bb_lower": ["bollinger", "bb", "band", "lower"],
        "ema50": ["ema", "moving average", "ma50"],
        "sma20": ["sma", "ma20"],
        "volume": ["volume", "vol"],
    }
    for ind_name, keywords in ind_map.items():
        if ind_name in indicators and any(k in lower_base for k in keywords):
            val = indicators[ind_name]
            if isinstance(val, float) and val > 1000:
                formatted = f"**${val:,.2f}**"
            elif isinstance(val, float):
                formatted = f"**{val:.1f}**"
            else:
                formatted = f"**{val}**"
            tail_parts.append(f"{ind_name.upper()}: {formatted}")

    # Support / Resistance — bold the price
    if supports and ("support" in lower_base or "level" in lower_base):
        s = min(supports)
        price_fmt = f"**${s:,.2f}**" if s >= 1 else f"**${s:.6f}**"
        tail_parts.append(f"Support: {price_fmt}")
    if resistances and ("resistance" in lower_base or "level" in lower_base):
        r = max(resistances)
        price_fmt = f"**${r:,.2f}**" if r >= 1 else f"**${r:.6f}**"
        tail_parts.append(f"Resistance: {price_fmt}")

    # Candlestick patterns — bold the name
    if patterns and ("pattern" in lower_base or "candle" in lower_base):
        tail_parts.append(f"Pattern: **{patterns[0]}**")

    # Matching finding as contextual note
    if not tail_parts:
        for f in findings:
            if any(w in f.lower() for w in lower_base.split()[:5]):
                tail_parts.append(f[:120])
                break

    if tail_parts:
        sep = "\\n\\n>  "
        return base + sep + " | ".join(tail_parts[:3])

    return base


def _intent_fallback_tour(
    user_query: str,
    chart_context: Optional[Dict[str, Any]],
    analysis_data: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Deterministic tour plan based on the user's intent keywords.

    Each step explanation is enriched with actual analytical data
    from analysis_data (extracted from the synthesis output) so the
    user sees real numbers, levels, and findings — not generic
    boilerplate.
    """
    lowered = user_query.lower().strip()
    if not lowered:
        return None

    current_symbol = (chart_context or {}).get("symbol", "BTCUSDT")
    target_symbol = _extract_symbol_from_query(user_query, current_symbol)
    want_symbol_switch = target_symbol != current_symbol

    # Shortcuts to analysis data
    trend = (analysis_data or {}).get("trend", "neutral")
    price = (analysis_data or {}).get("price_current")
    indicators = (analysis_data or {}).get("indicators", {})
    supports = (analysis_data or {}).get("support_levels", [])
    resistances = (analysis_data or {}).get("resistance_levels", [])
    findings = (analysis_data or {}).get("key_findings", [])

    def exp(base: str) -> str:
        return _fmt_explanation(base, analysis_data)

    steps: List[Dict[str, Any]] = []
    title = None

    # ── Recent trades intent ──
    if any(tok in lowered for tok in ("recent trades", "trades panel", "trade panel", "latest trades", "trade history", "matched trades", "recent prints")):
        title = f"{target_symbol} recent trades walkthrough"
        if want_symbol_switch:
            steps.append({"action_type": "set_symbol", "params": {"symbol": target_symbol}, "explanation": exp(f"Switching the chart to {target_symbol} so recent trades match the requested market.")})
        steps.append({"action_type": "highlight_candles", "params": {"from_index": -10, "to_index": -1, "label": "Recent price action"}, "explanation": exp("Looking at the latest candles before opening time-and-sales so trades line up with recent price movement.")})
        steps.append({"action_type": "open_panel", "params": {"target": "trades"}, "explanation": exp("Opening the recent trades panel — this shows executed trades, size, and aggressor flow near the current price.")})

    # ── Order book intent ──
    elif any(tok in lowered for tok in ("order book", "orderbook", "depth", "liquidity", "bids", "asks", "sổ lệnh", "độ sâu", "thanh khoản")):
        title = f"{target_symbol} order book walkthrough"
        if want_symbol_switch:
            steps.append({"action_type": "set_symbol", "params": {"symbol": target_symbol}, "explanation": exp(f"Switching the chart to {target_symbol} so the order book shows the right market.")})
        steps.append({"action_type": "highlight_candles", "params": {"from_index": -10, "to_index": -1, "label": "Last 10 candles"}, "explanation": exp("Looking at the most recent candles to see current price context for order book liquidity.")})
        steps.append({"action_type": "open_panel", "params": {"target": "orderBook"}, "explanation": exp("Opening the live order book — bids stacked below price, asks above. Large walls often mark support/resistance.")})

    # ── Compare intent ──
    elif any(tok in lowered for tok in ("compare", "vs", "versus", "against", "between", "so sánh", "giữa", "khác")):
        symbols = []
        for sym, pats in _SYMBOL_PATTERNS:
            if any(p in lowered for p in pats):
                symbols.append(f"{sym}USDT")
        if len(symbols) >= 2:
            title = f"Compare {symbols[0].replace('USDT', '')} vs {symbols[1].replace('USDT', '')}"
            steps.append({"action_type": "add_indicator", "params": {"indicator": "ema50"}, "explanation": exp("Adding the 50 EMA so we can compare both assets' trend posture on the same indicator.")})
            for sym in symbols[:2]:
                steps.append({"action_type": "set_symbol", "params": {"symbol": sym}, "explanation": exp(f"Switching to {sym} so you can see its setup on the chart.")})
                steps.append({"action_type": "highlight_candles", "params": {"from_index": -20, "to_index": -1, "label": f"{sym} recent action"}, "explanation": exp(f"Last 20 candles of {sym} action for trend context.")})

    # ── News / market overview intent ──
    elif any(tok in lowered for tok in ("news", "headlines", "market overview", "broader market", "macro", "tin tức", "thị trường", "vĩ mô")):
        title = "News & market overview"
        steps.append({"action_type": "highlight_candles", "params": {"from_index": -10, "to_index": -1, "label": "Recent action"}, "explanation": exp("Current price action on the chart before we pop over to the news feed for broader context.")})
        steps.append({"action_type": "switch_app_view", "params": {"view": "marketsNews"}, "explanation": exp("Opening the Markets & News view for the latest headlines and broader market context.")})

    # ── Analyze intent — THE MOST IMPORTANT PATH, enriched with analysis data ──
    elif any(tok in lowered for tok in (
        "analyze", "analysis", "review", "what do you see", "thoughts on", "look at",
        "phân tích", "đánh giá", "nhận xét",
        "yesterday", "today", "tonight", "last week", "last night",
        "this week", "this month", "this morning", "hôm qua", "tuần", "tháng",
        "what can you say", "what's happening", "what is happening", "whats happening",
        "what do you think", "your thoughts", "give me", "tell me about",
        "trend", "moving average trend", "price action", "market action", "market today", "price today",
        "price now", "how is", "how's", "cách", "thế nào", "như thế nào",
        "btc", "eth", "sol", "doge", "bitcoin", "ethereum", "solana", "bnb", "xrp",
        "coin", "crypto", "currency", "asset", "tiền", "đồng",
    )):
        title = f"{target_symbol} analysis"

        if want_symbol_switch:
            steps.append({"action_type": "set_symbol", "params": {"symbol": target_symbol}, "explanation": exp(f"Switching the chart to {target_symbol} so the analysis is anchored to the right market.")})

        # Step 1: Timeframe — inject trend + price
        price_str = f" Price at ${price:,.2f}." if price else ""
        trend_emoji = "🟢" if trend == "bullish" else ("🔴" if trend == "bearish" else "⚪")
        trend_str = f" Trend: {trend_emoji} {trend}." if trend != "neutral" else ""
        steps.append({
            "action_type": "set_timeframe",
            "params": {"timeframe": "1h"},
            "explanation": exp(f"Switching to the 1h timeframe so you can see {target_symbol}'s recent price action clearly.{price_str}{trend_str}"),
        })

        # Step 2: Highlight candles — inject price + S/R + key findings
        sr_str = ""
        if supports: sr_str += f" Support: ${min(supports):,.2f}."
        if resistances: sr_str += f" Resistance: ${max(resistances):,.2f}."
        find_str = f"\\n\\n>  {findings[0]}" if findings else ""
        steps.append({
            "action_type": "highlight_candles",
            "params": {"from_index": -24, "to_index": -1, "label": "Recent action"},
            "explanation": exp(f"Highlighting the last 24 candles of {target_symbol} — the setup we are analyzing.{sr_str}{find_str}"),
        })

        # Step 3: Resistance line
        r_str = f" Analysis identifies resistance near ${max(resistances):,.2f}." if resistances else " Resistance price has struggled to break above."
        steps.append({
            "action_type": "draw_horizontal_line",
            "params": {"label": "Resistance level"},
            "explanation": exp(f"Drawing a horizontal line at the recent swing high.{r_str} A break above with volume confirms bullish continuation."),
        })

        # Step 4: RSI — inject actual value (interleaved between S/R for variety)
        rsi_val = indicators.get("rsi")
        if rsi_val is not None:
            zone = "overbought (>70)" if rsi_val > 70 else ("oversold (<30)" if rsi_val < 30 else "neutral (30-70)")
            rsi_str = f" Currently at {rsi_val:.1f} ({zone})."
        else:
            rsi_str = ""
        steps.append({
            "action_type": "add_indicator",
            "params": {"indicator": "rsi"},
            "explanation": exp(f"RSI (Relative Strength Index) measures momentum.{rsi_str} Watch for divergences between RSI and price — these often signal reversals."),
        })

        # Step 5: Support line (not consecutive with resistance line)
        s_str = f" Analysis identifies support near ${min(supports):,.2f}." if supports else " Support zone where buyers stepped in."
        steps.append({
            "action_type": "draw_horizontal_line",
            "params": {"label": "Support level"},
            "explanation": exp(f"Drawing a horizontal line at a key support level.{s_str} A break below signals bearish continuation."),
        })

        # Step 6: EMA50 — inject relative price position
        ema_val = indicators.get("ema50")
        if ema_val is not None and price is not None:
            above_below = "above" if price > ema_val else "below"
            ema_str = f" Price is {above_below} the 50 EMA (${ema_val:,.2f}), confirming {trend} bias."
        else:
            ema_str = ""
        steps.append({
            "action_type": "add_indicator",
            "params": {"indicator": "ema50"},
            "explanation": exp(f"Adding the 50 EMA to confirm trend direction.{ema_str} Watch for the EMA as dynamic support/resistance."),
        })

    # ── Indicator tutorial intent ──
    elif any(tok in lowered for tok in ("rsi", "macd", "bollinger", "indicator", "moving average", "sma", "ema", "chỉ báo", "chỉ số")):
        title = "Technical indicators"
        if "rsi" in lowered:
            rsi_val = indicators.get("rsi")
            rsi_suffix = f" Currently at {rsi_val:.1f}." if rsi_val is not None else ""
            steps.append({"action_type": "add_indicator", "params": {"indicator": "rsi"}, "explanation": exp(f"RSI (Relative Strength Index) measures momentum on a 0-100 scale.{rsi_suffix} >70 = overbought, <30 = oversold.")})
        if "macd" in lowered:
            macd_val = indicators.get("macd")
            macd_suffix = f" Currently at {macd_val:.1f}." if macd_val is not None else ""
            steps.append({"action_type": "add_indicator", "params": {"indicator": "macd"}, "explanation": exp(f"MACD shows momentum direction (line) and strength (histogram).{macd_suffix} Crosses above the signal line are bullish.")})
        if "bollinger" in lowered or "bb" in lowered:
            bb_u = indicators.get("bb_upper")
            bb_l = indicators.get("bb_lower")
            bb_str = ""
            if bb_u is not None and bb_l is not None:
                bb_str = f" Upper: ${bb_u:,.2f}, Lower: ${bb_l:,.2f}."
            steps.append({"action_type": "add_indicator", "params": {"indicator": "bb"}, "explanation": exp(f"Bollinger Bands show volatility.{bb_str} Squeezes often precede big moves.")})
        if "ema" in lowered or "sma" in lowered or "moving average" in lowered:
            ema_val = indicators.get("ema50")
            ema_suffix = f" EMA50 at ${ema_val:,.2f}." if ema_val is not None else ""
            steps.append({"action_type": "add_indicator", "params": {"indicator": "sma20"}, "explanation": exp(f"SMA 20 (20-period simple moving average) smooths out price.{ema_suffix} Price above = bullish bias.")})

    # ── Support / Resistance intent ──
    elif any(tok in lowered for tok in (
        "support", "resistance", "s/r", "key level", "price level",
        "hỗ trợ", "kháng cự", "ngưỡng",
    )):
        title = f"{target_symbol} support & resistance"
        if want_symbol_switch:
            steps.append({"action_type": "set_symbol", "params": {"symbol": target_symbol}, "explanation": exp(f"Switching chart to {target_symbol} for S/R analysis.")})

        sr_context = ""
        if supports: sr_context += f" Support near ${min(supports):,.2f}."
        if resistances: sr_context += f" Resistance near ${max(resistances):,.2f}."

        steps.append({"action_type": "set_timeframe", "params": {"timeframe": "1h"}, "explanation": exp(f"1h chart gives a clear view of key price levels.{sr_context}")})
        steps.append({"action_type": "highlight_candles", "params": {"from_index": -30, "to_index": -1, "label": "Price action zone"}, "explanation": exp(f"Recent price action — support at bounce lows, resistance at rejection highs.{sr_context}")})

        r_lvl = resistances[0] if resistances else None
        r_line = f" Drawing at ${r_lvl:,.2f} (identified in analysis)." if r_lvl else " Drawing at the recent high."
        steps.append({"action_type": "draw_horizontal_line", "params": {"label": "Key resistance level"}, "explanation": exp(f"Horizontal line at resistance.{r_line} Break above = bullish signal.")})

        # Brief candle check between S/R lines to avoid consecutive dup
        candle_price_str = f" Price at ${price:,.2f}." if price else ""
        steps.append({"action_type": "highlight_candles", "params": {"from_index": -5, "to_index": -1, "label": "Price inside range"}, "explanation": exp(f"Checking where price sits relative to these levels.{candle_price_str}")})

        s_lvl = supports[0] if supports else None
        s_line = f" Drawing at ${s_lvl:,.2f} (identified in analysis)." if s_lvl else " Drawing at the recent low."
        steps.append({"action_type": "draw_horizontal_line", "params": {"label": "Key support level"}, "explanation": exp(f"Horizontal line at support.{s_line} Break below = bearish continuation.")})

    # ── Chart type change intent ──
    elif any(tok in lowered for tok in (
        "heikin ashi", "heikin-ashi", "heiken ashi",
        "candle type", "chart type", "switch to",
        "biểu đồ nến", "loại nến",
    )):
        title = f"{target_symbol} chart type change"
        if want_symbol_switch:
            steps.append({"action_type": "set_symbol", "params": {"symbol": target_symbol}, "explanation": exp(f"Switching to {target_symbol}.")})
        steps.append({"action_type": "set_chart_type", "params": {"chart_type": "heikin_ashi"}, "explanation": exp(f"Switching to Heikin-Ashi candles — they smooth out noise and make trends easier to spot.{' The current trend is ' + trend + '.' if trend != 'neutral' else ''}")})

    # ── Highlight / drawing intent ──
    elif any(tok in lowered for tok in (
        "highlight", "draw", "fibonacci", "fib", "trendline", "trend line",
        "vẽ", "đường",
    )):
        title = f"{target_symbol} chart annotations"
        if want_symbol_switch:
            steps.append({"action_type": "set_symbol", "params": {"symbol": target_symbol}, "explanation": exp(f"Switching to {target_symbol}.")})
        price_ctx = f" Price at ${price:,.2f}." if price else ""
        steps.append({"action_type": "highlight_candles", "params": {"from_index": -20, "to_index": -1, "label": "Highlighted area"}, "explanation": exp(f"Highlighting recent price action for drawing context.{price_ctx}")})
        if "fib" in lowered or "fibonacci" in lowered:
            steps.append({"action_type": "draw_fib", "params": {}, "explanation": exp("Drawing Fibonacci retracement from swing low to swing high — key levels at 0.382, 0.5, 0.618 often act as S/R.")})
        else:
            steps.append({"action_type": "draw_horizontal_line", "params": {"label": "Reference line"}, "explanation": exp(f"Drawing a reference line you can track as price moves.{price_ctx}")})

    if not steps or title is None:
        return None

    # Build a richer summary using analysis findings
    summary_parts = [f"## {title}"]
    if findings:
        summary_parts.append(findings[0][:200])
    if len(findings) > 1:
        summary_parts.append(findings[1][:200])

    return {
        "title": title,
        "steps": steps,
        "summary": "\n\n".join(summary_parts),
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
        # Vietnamese triggers
        "hướng dẫn", "cách sử dụng", "làm thế nào",
        "tour", "chỉ dẫn", "chỉ cho tôi",
        "lmview là gì", "ứng dụng này", "tính năng",
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
        steps.append(PlannedStep(
            action_type=action_name,
            params=s.action.get("arguments", {}),
            explanation=s.explanation,
            target_selector=s.target_selector,
            requires_approval=s.requires_approval,
        ))
    if not steps:
        logger.warning("LMView workspace tour produced 0 valid steps.")
        return None
    walkthrough_steps = [
        WalkthroughStep(
            explanation=step.explanation,
            actions=[_guided_action_from_step(step)],
            keep_effects=True,
            chart_freeze=True,
        )
        for step in steps
    ]
    return TourPlan(
        tour_id=template.tour_id,
        title=template.title,
        steps=walkthrough_steps,
        summary=template.description,
        chart_snapshot=None,
    )
