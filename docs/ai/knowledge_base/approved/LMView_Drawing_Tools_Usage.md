# LMView Drawing Tools Usage

> **Metadata**: `review_status: approved` | `allowed_for_rag: true` | `internal_only: false`
> **Version scope**: 0.25.x | **Last reviewed**: 2026-06-16

## Overview
LMView provides a comprehensive suite of drawing tools designed to help traders perform technical analysis directly on the chart. These tools are rendered in data-space coordinates, ensuring they remain aligned with the candles during zoom, pan, or timeframe changes.

## Available Drawing Tools
- **Trend Line**: Draws a straight line between two points to identify trends.
- **Horizontal Line / Horizontal Ray**: Marks specific price levels. A Horizontal Ray starts from an anchor point and extends infinitely to the right.
- **Vertical Line**: Marks specific time points on the chart.
- **Fibonacci Retracement**: Uses a two-point anchor (high/low or low/high) to draw retracement levels (0.236, 0.382, 0.5, 0.618, etc.). The background fill renders behind the lines.
- **Parallel Channel**: Uses a three-anchor flow to draw a main trend line and a parallel offset line, creating a channel.
- **Long / Short Position**: Visualizes risk/reward for potential trades. Uses a two-anchor commit to define entry, stop-loss, and take-profit areas.
- **Text / Note**: Adds anchored text or small notes to specific chart points. Stays anchored to the data coordinates.
- **Measurement / Ruler**: Calculates price and time distance between two points, displaying change percentage and duration.
- **Rectangle**: Highlights specific price zones (e.g., consolidation areas).

## Usage Instructions
1. **Selecting a Tool**: Click on the desired tool from the left drawing toolbar. Favorite tools can be pinned to the top of the toolbar in Settings.
2. **Placing Anchors**: Click on the chart to set anchor points. Tools like the Horizontal Ray and Vertical Line require a single click. Tools like Trend Line and Fibonacci require two clicks. Parallel Channel requires three clicks.
3. **Editing**: Click on an existing drawing to select it. You can then drag its anchor points to adjust it, or press Delete / the Trash icon to remove it.
4. **Visibility**: Drawings are saved to your session/account and persist across reloads.
