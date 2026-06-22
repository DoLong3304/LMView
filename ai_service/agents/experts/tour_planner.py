"""
Tour Planner — converts expert analysis into step-by-step guided tours for Interact mode.

Runs after the full pipeline completes (scope → experts → synthesis). Takes
all expert outputs + synthesized response and plans a multi-step chart tour.

Each step maps to an action_type supported by the frontend action system.
The user progresses through steps at their own pace.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

from backend.models.ai.tour import TourPlan, TourStepAction

logger = logging.getLogger("ai_service.agents.experts.tour_planner")

# ── Supported action types the tour planner can emit ─────────────────────────

SUPPORTED_ACTIONS = [
    "highlight_section",
    "highlight_chart_area",
    "highlight_candles",
    "add_indicator",
    "remove_indicator",
    "draw_tool",
    "draw_trendline",
    "set_timeframe",
    "set_chart_type",
    "create_annotation",
]

# ── LLM Prompt ───────────────────────────────────────────────────────────────

TOUR_PLANNER_SYSTEM_PROMPT = """You are LMView's chart analysis tour guide. Your job is to convert raw market analysis into a step-by-step interactive tour that teaches the user about the current market situation through hands-on chart exploration.

## Rules
1. Break the analysis into 2-5 logical steps. Each step is one chart action + explanation.
2. Each step must use one of these action types: {action_types}
3. Each step's explanation must be educational — teach the user WHY this matters.
4. Start simple, build complexity. First show what to look at, then add indicators/tools.
5. End with a helpful summary of what the user learned.
6. Never propose actions that change the user's data (no place orders, no delete).
7. Use highlight_section steps sparingly — only when user needs to look at a specific UI area.
8. When highlighting chart areas, use highlight_chart_area with left_pct, top_pct, width_pct, height_pct (0-100 percentages).

## Available action types
- highlight_section: Dim everything except a UI section. params: {{"target": "chart|chartCanvas|chartToolbar|drawingTools|ai|rightPanelOverview|watchlist|orderBook|recentTrades|settings"}}
- highlight_chart_area: Highlight a rect within the chart. params: {{"left_pct": 0-100, "top_pct": 0-100, "width_pct": 0-100, "height_pct": 0-100, "label": "...", "message": "..."}}
- highlight_candles: Highlight candle range. params: {{"from_index": N, "to_index": N, "label": "...", "message": "..."}}
- add_indicator: Show an indicator. params: {{"indicator": "rsi|macd|sma20|sma50|ema12|ema26|bollinger_bands|vwap|volume_ma"}}
- remove_indicator: Hide an indicator. Same params as add_indicator.
- draw_tool: Select a drawing tool. params: {{"tool": "trendline|fibonacci|rectangle|cursor", "points": [{{"time": unix_sec, "price": value}}, ...], "text": "..."}}
- set_timeframe: Change timeframe. params: {{"timeframe": "1m|5m|15m|1h|4h|1d|1w"}}
- set_chart_type: Change chart type. params: {{"chart_type": "candles|bars|line|area|heikinAshi"}}
- create_annotation: Add text label. params: {{"time": epoch_ms, "price": number, "text": "..."}}

## Output format
Respond with ONLY valid JSON. No markdown, no code fences, no explanation outside JSON.
{{
  "tour_plan": {{
    "title": "Short tour title",
    "steps": [
      {{
        "action_type": "...",
        "params": {{...}},
        "explanation": "Educational explanation of this step..."
      }}
    ],
    "summary": "Concise recap of what was covered..."
  }}
}}

If you cannot create a meaningful tour (e.g., insufficient data), respond with:
{{"tour_plan": null, "reason": "Explain why no tour could be created."}}
"""


async def plan_tour(
    user_query: str,
    expert_outputs: Dict[str, Any],
    synthesized_response: str,
    chart_context: Optional[Dict[str, Any]],
    mode: str,
) -> Optional[TourPlan]:
    """Plan a guided analysis tour from pipeline outputs.

    Args:
        user_query: Original user message.
        expert_outputs: All expert outputs from pipeline execution.
        synthesized_response: The final LLM response text.
        chart_context: Current chart context (symbol, timeframe, candles).
        mode: Chat mode ("ask" or "interact").

    Returns:
        TourPlan if successful, None if mode isn't interact or planning fails.
    """
    if mode != "interact":
        return None

    start_ms = time.monotonic_ns() // 1_000_000

    # Build context for the LLM
    context = _build_tour_context(user_query, expert_outputs, synthesized_response, chart_context)

    # Call LLM to plan the tour
    tour_plan_data = await _llm_plan_tour(context)

    if tour_plan_data is None:
        logger.info("Tour planner returned null — no tour created.")
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
        from ai_service.providers.router import ProviderRouter
        from backend.models.ai.providers import LLMCompletionRequest

        router = ProviderRouter()
        provider = await router.get_provider()

        request = LLMCompletionRequest(
            messages=[
                {"role": "system", "content": TOUR_PLANNER_SYSTEM_PROMPT.format(
                    action_types=", ".join(SUPPORTED_ACTIONS),
                )},
                {"role": "user", "content": context},
            ],
            temperature=0.3,
            max_tokens=2000,
        )

        response = await provider.complete(request)

        content = (response.choices[0].message.content or "").strip()
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
