# LMView AI Usage: Ask and Interact Modes

> **Metadata**: `review_status: approved` | `allowed_for_rag: true` | `internal_only: false`
> **Version scope**: 0.25.x | **Last reviewed**: 2026-06-16

## Overview
The LMView AI Assistant is designed to help users perform technical analysis, understand market conditions, and navigate the platform. It operates in two primary modes: Ask Mode and Interact Mode.

## Context Awareness
The AI Assistant is always aware of your current chart context. When you open the AI Assistant panel, it knows:
- The currently selected asset (e.g., BTC/USDT)
- The active timeframe (e.g., 1m, 1h, 1d)
- Active technical indicators (e.g., SMA, RSI)
- Recent price action and market metrics

## Ask Mode (Educational & Analytical)
In Ask Mode, the AI acts as an educational co-pilot.
- **Capabilities**: Explains technical indicators, analyzes the current chart setup, provides information from the knowledge base, and summarizes market news sentiment.
- **Limitations**: The AI does NOT provide financial advice. It cannot execute trades, manage portfolios, or access the external internet.
- **Bilingual**: The assistant supports English and Vietnamese, adapting to the user's preferred language.

## Interact Mode (UI Orchestration)
Interact Mode extends the AI's capabilities by allowing it to propose actions within the LMView interface.
- **Capabilities**: The AI can suggest adding/removing indicators, changing timeframes, navigating to different panels (e.g., Watchlist, Order Book, Screener), and highlighting specific UI elements.
- **Safety**: All proposed actions require explicit user approval before execution. The AI will never modify your settings or chart without your permission.
- **Workflow**: When you ask the AI to "add an RSI indicator", it will generate an action proposal. You click "Approve", and the platform executes the action.
