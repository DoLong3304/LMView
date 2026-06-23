"""Tour template definitions for guided interactive analysis steps.

Each tour is a sequence of Interact-mode actions with accompanying
explanations shown in a step overlay.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TourStep:
    """A single step in a guided analysis."""
    action: Dict[str, Any]  # {name, arguments} — Interact mode action
    explanation: str
    requires_approval: bool = False
    target_selector: Optional[str] = None  # CSS selector to highlight


@dataclass
class TourTemplate:
    """Complete guided analysis template."""
    tour_id: str
    title: str
    description: str
    steps: List[TourStep]


# ── Tour Registry ────────────────────────────────────────────────────────────

WORKSPACE_OVERVIEW_TOUR = TourTemplate(
    tour_id="lmview-overview",
    title="Welcome to LMView",
    description=(
        "LMView is a real-time crypto technical-analysis platform. "
        "Here's a quick walkthrough of its key features."
    ),
    steps=[
        # Step 1: highlight the chart panel
        TourStep(
            action={
                "name": "highlight_section",
                "arguments": {
                    "target": "chart",
                    "label": "Chart workspace",
                    "message": (
                        "This is the main candlestick chart. "
                        "Price scale is on the right, time along the bottom."
                    ),
                },
            },
            explanation=(
                "The main chart shows real-time OHLCV candlesticks across "
                "15 timeframes (1s to 1M). Every Interact-mode step in this "
                "tour will operate on this chart, so let's get oriented first."
            ),
            requires_approval=False,
            target_selector="[data-ai-section='chart']",
        ),
        # Step 2: highlight the drawing tools toolbar
        TourStep(
            action={
                "name": "highlight_section",
                "arguments": {
                    "target": "drawingTools",
                    "label": "Drawing tools",
                    "message": (
                        "Trendlines, channels, Fibonacci, and 30+ drawing tools "
                        "live here."
                    ),
                },
            },
            explanation=(
                "The left toolbar has 30+ drawing tools: trendlines, rectangles, "
                "Fibonacci retracements, parallel channels, Gann boxes, and "
                "pattern overlays. You can also ask the AI to draw on the chart "
                "for you in Interact mode."
            ),
            requires_approval=False,
            target_selector="[data-ai-section='drawingTools']",
        ),
        # Step 3: add RSI indicator to show it live
        TourStep(
            action={
                "name": "add_indicator",
                "arguments": {"indicator": "rsi"},
            },
            explanation=(
                "RSI (Relative Strength Index) measures momentum on a 0-100 scale. "
                "Above 70 = overbought (potential reversal down), below 30 = oversold "
                "(potential reversal up). It appears as a sub-pane under the chart."
            ),
            requires_approval=False,
        ),
        # Step 4: open the order book panel
        TourStep(
            action={
                "name": "open_panel",
                "arguments": {
                    "target": "orderBook",
                    "label": "Order book",
                    "message": "Live bids and asks near the current price.",
                },
            },
            explanation=(
                "The right panel switches between the order book (live bids/asks), "
                "recent trades, watchlist, and market overview. We're opening the "
                "order book so you can see live liquidity near the current price."
            ),
            requires_approval=False,
        ),
        # Step 5: highlight the AI panel itself
        TourStep(
            action={
                "name": "highlight_section",
                "arguments": {
                    "target": "ai",
                    "label": "AI Helper",
                    "message": (
                        "Ask questions in Ask mode or let Interact mode "
                        "walk you through the chart visually."
                    ),
                    "include_chat": True,
                },
            },
            explanation=(
                "You're using the AI Helper right now. Toggle to Ask mode for a "
                "chat-only Q&A, or stay in Interact mode to get visual chart "
                "walkthroughs like this one. Try asking 'Analyze BTC' to see "
                "another Interact-mode tour."
            ),
            requires_approval=False,
            target_selector="[data-ai-section='ai']",
        ),
    ],
)

INDICATOR_TUTORIAL_TOUR = TourTemplate(
    tour_id="indicator-tutorial",
    title="Technical Indicators",
    description="A walkthrough of common technical indicators and their signals.",
    steps=[
        TourStep(
            action={"name": "add_indicator", "arguments": {"indicator": "sma20"}},
            explanation=(
                "SMA 20 — 20-period Simple Moving Average. Price above SMA20 "
                "suggests bullish momentum; below suggests bearish. It's a slow, "
                "smoothed line that lags price but filters out noise."
            ),
            requires_approval=False,
        ),
        TourStep(
            action={"name": "add_indicator", "arguments": {"indicator": "ema12"}},
            explanation=(
                "EMA 12 — 12-period Exponential Moving Average. Reacts faster to "
                "recent prices than SMA. When EMA12 crosses above SMA20 it's a "
                "common bullish signal (a 'golden cross' on smaller scales)."
            ),
            requires_approval=False,
        ),
        TourStep(
            action={"name": "add_indicator", "arguments": {"indicator": "macd"}},
            explanation=(
                "MACD — Moving Average Convergence Divergence. Shows momentum "
                "direction (line) and strength (histogram). When the MACD line "
                "crosses above the signal line and the histogram turns positive, "
                "that's a bullish momentum confirmation."
            ),
            requires_approval=False,
        ),
        TourStep(
            action={"name": "add_indicator", "arguments": {"indicator": "rsi"}},
            explanation=(
                "RSI — Relative Strength Index (0-100). Confirms momentum strength: "
                ">70 = overbought (potential reversal down), <30 = oversold "
                "(potential reversal up). Divergences between RSI and price often "
                "precede trend reversals."
            ),
            requires_approval=False,
        ),
    ],
)

# All available tours
AVAILABLE_TOURS = {
    t.tour_id: t
    for t in [WORKSPACE_OVERVIEW_TOUR, INDICATOR_TUTORIAL_TOUR]
}
