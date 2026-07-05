# LMView AI Usage — Ask Mode and Interact Mode Complete Guide

> **Document Type**: Feature Reference
> **Audience**: AI Assistant, End Users
> **Version**: 0.27.0+
> **Domain**: AI Assistant, LMView Platform Features

---

## Table of Contents

1. Overview of LMView AI Assistant
2. Context Awareness
3. Ask Mode (Educational & Analytical)
   - 3.1 Capabilities
   - 3.2 Data Sources
   - 3.3 Language Support (English/Vietnamese)
   - 3.4 Knowledge Base Grounding
   - 3.5 Limitations
4. Interact Mode (UI Orchestration)
   - 4.1 Capabilities
   - 4.2 Available Chart Actions
   - 4.3 Action Approval Workflow
   - 4.4 Action Types in Detail
   - 4.5 Tour (Platform Guidance)
   - 4.6 Limitations
5. AI Model Selection
   - 5.1 Tier System
   - 5.2 Model Options
   - 5.3 Auto Mode
6. Response Caching
7. Financial Safety Protections
   - 7.1 Always-Included Disclaimers
   - 7.2 Prohibited Behaviors
   - 7.3 Knowledge Boundary
8. Bilingual Support Details
9. Practical Usage Examples
   - 9.1 Ask Mode Examples
   - 9.2 Interact Mode Examples
10. References

---

## 1. Overview of LMView AI Assistant

The LMView AI Assistant is an integrated market analysis tool embedded in the LMView dashboard. It provides real-time cryptocurrency technical analysis, educational explanations, and safe UI orchestration — all within the user's chart context.

The AI operates in two primary modes, selectable from the AI Assistant panel:

- **Ask Mode** (default) — Ask questions, get analysis and explanations. The AI reads the chart, indicators, news, and knowledge base to provide informed responses.
- **Interact Mode** — Same analysis as Ask Mode, plus the AI can propose chart actions (add indicators, draw tools, navigate to panels). All actions require user approval.

**Architecture**: The AI runs as a standalone `ai-service` container (port 8100) using a LangGraph-based pipeline. It does not execute trades, manage wallets, or access the internet during conversations. It is grounded by approved RAG knowledge base documents and real-time market data from the LMView backend.

---

## 2. Context Awareness

When you open the AI Assistant panel, it automatically reads your current chart context:

| Context Element | Detail | Example |
|---|---|---|
| **Current symbol** | Selected trading pair | BTC/USDT, ETH/USDT |
| **Exchange** | Data source exchange | Binance (primary), OKX (if enabled) |
| **Timeframe** | Current chart timeframe | 1m, 5m, 1H, 4H, 1D, 1W |
| **Visible range** | Time range visible on chart | Last 24 hours, last 7 days |
| **Active indicators** | Indicators currently enabled | RSI(14), SMA(50/200), MACD |
| **Candle data** | Recent OHLCV data | Last ~100 candles |
| **Indicator values** | Current calculated values | RSI: 58.2, SMA50: 49,500 |
| **Market data** | Ticker, order book, trades | Price, volume, spread, depth |
| **Active drawings** | Existing annotations | Trendlines, Fibonacci levels, notes |

### 2.1 Session Memory (Cross-Turn Context)

> *Available since v0.31.0*

The AI maintains **cross-turn session memory** within a chat session. Key findings from each exchange are extracted and stored, allowing the AI to:

- **Remember your preferences** — If you specify a preferred timeframe for analysis, the AI retains that preference across subsequent questions.
- **Recall prior analyses** — Yesterday's analysis of BTC resistance levels is available when you continue the session today.
- **Prevent context decay** — In long conversations (6+ messages), session memory is injected as a system prompt to keep earlier findings relevant.
- **Automatic compaction** — After 10 exchanges, older messages are summarized while preserving key findings. The session continues without losing context.

Session memory is stored in the database (PostgreSQL `context_summary` column on `ai_chat_sessions`). It persists across browser refreshes and page loads, so your analysis thread continues seamlessly.

**What is remembered**: Key price levels mentioned, indicator interpretations, user preferences (e.g., "I prefer the 4H chart"), conclusions from previous analyses.

**What is not remembered**: Exact candle data from previous sessions (only analytical findings), personal user information, credentials, or account details.

The AI also has access to the broader market context:
- **Market overview** — Top movers, sector performance, heatmap.
- **News** — Recent news articles with sentiment analysis for the current symbol and related assets.
- **Support/Resistance levels** — Calculated key levels for the current symbol.

---

## 3. Ask Mode (Educational & Analytical)

### 3.1 Capabilities

In Ask Mode, the AI acts as an expert co-pilot. It can:

- **Explain technical indicators** — "What does RSI divergence mean?", "How is MACD calculated?"
- **Analyze the current chart** — "Is BTC in an uptrend?", "What support/resistance levels do you see?"
- **Answer trading concept questions** — "What is the difference between market and limit orders?", "How does impermanent loss work?"
- **Summarize market news sentiment** — "What's the sentiment on ETH right now?", "Any major news for SOL?"
- **Compare historical patterns** — "Has BTC acted this way before similar halvings?"
- **Provide multi-timeframe analysis** — "What do you see on 4H and daily?"
- **Explain platform features** — "How do I use the Fibonacci drawing tool?", "How do I add an indicator?"
- **Respond in English or Vietnamese** — Language auto-detection is built in.

### 3.2 Data Sources

Ask Mode uses the following data sources, prioritized from fastest to most comprehensive:

| Source | Data Type | Freshness |
|---|---|---|
| **Redis live cache** | Candle data, ticker, order book depth, trade tape | Sub-second to seconds |
| **InfluxDB** | Historical klines and indicator values | Seconds |
| **PostgreSQL** | News/sentiment, chat sessions, knowledge base | 5-minute refresh |
| **Trino** | Market overview, dominance, sector data | Minutes (Dagster-scheduled) |
| **RAG Knowledge Base** | Approved documents (TA, crypto education, risk management) | Static, updated on ingest |

### 3.3 Language Support (English/Vietnamese)

The AI Assistant supports bilingual conversations:

- **Auto-detection** — The AI detects the user's language based on character patterns. If the message contains >2% Vietnamese characters (accented characters like ô, ơ, ê, ư, ả, ẽ, ị), it responds in Vietnamese.
- **Reasoning quality preserved** — The AI thinks through analysis in English first, then translates output to Vietnamese for quality.
- **Glossary consistency** — Standard Vietnamese trading terms are maintained throughout responses (see `Bilingual_Glossary.md` for the full term mapping).

### 3.4 Knowledge Base Grounding

All AI responses are grounded by an approved RAG (Retrieval-Augmented Generation) knowledge base containing:

- LMView platform documentation (system architecture, function calling, drawing tools, indicators).
- Crypto education (fundamentals, technical analysis, order flow, on-chain analytics).
- Risk management frameworks.
- DeFi analysis, market microstructure, correlation analysis.
- Drawing tools reference.

The knowledge base has 23+ approved sources, each with credibility levels and review status. When the knowledge base conflicts with the AI's training data, the AI is instructed to **prefer the knowledge base** and explicitly note the conflict.

For queries outside the knowledge boundary (weather, medical advice, stock recommendations), the AI gracefully declines and redirects to crypto market analysis topics.

### 3.5 Limitations

- **Does not provide financial advice.** All analysis is educational.
- **Does not execute trades or manage positions.**
- **Cannot access the internet or external APIs during a conversation.**
- **Cannot run code, SQL queries, or shell commands.**
- **Cannot access other users' sessions or data.**
- **Cannot guarantee price predictions.** Market analysis is probabilistic.
- **Indicator values may differ** between Flink real-time and Spark batch due to different calculation methods.
- **News sentiment is automated** — scores are estimates, not human judgments.

---

## 4. Interact Mode (UI Orchestration)

Interact Mode extends Ask Mode with the ability to **propose actions** within the LMView interface. This allows the AI to demonstrate analysis visually on the chart rather than just describing it.

### 4.1 Capabilities

All Ask Mode capabilities PLUS:

- Add or remove technical indicators on the chart.
- Change the chart timeframe.
- Navigate to different panels (Watchlist, Order Book, Trade Tape, News, Screener).
- Draw annotation tools (trendlines, Fibonacci, rectangles, ellipses, text notes).
- Highlight specific candles, ranges, or zones on the chart.
- Remove existing drawings.
- Toggle chart type, log scale, or crosshair visibility.
- Start a guided tour of platform features.

### 4.2 Available Chart Actions

Interact Mode supports **40+ typed tool definitions**, all validated before execution:

| Category | Available Actions | Example |
|---|---|---|
| **Indicators** | add_indicator, remove_indicator | "Add RSI with period 14" |
| **Timeframe** | set_timeframe | "Switch to 4H chart" |
| **Visible range** | set_visible_range | "Zoom out to show last month" |
| **Chart type** | set_chart_type, set_log_scale | "Switch to Heikin-Ashi" |
| **Navigation** | navigate | "Open the order book panel" |
| **Drawings** | add_drawing, remove_drawing, clear_all_drawings | "Draw a Fibonacci retracement" |
| **Highlight** | highlight_candles, highlight_region, highlight_chart_area, highlight_contextual_zone, highlight_section | "Highlight oversold zone" |
| **Tour** | start_tour | "Show me how to use the platform" |
| **Utility** | toggle_crosshair, set_chart_style | |

### 4.3 Action Approval Workflow

Every proposed action follows a **mandatory approval workflow**:

1. **AI proposes** → The AI suggests an action with parameters.
2. **User reviews** → A modal/card displays the action details (what will happen).
3. **User approves or rejects** → The user clicks Approve, Reject, or Modify.
4. **AI executes** → Only upon explicit approval.
5. **Result reported** → The AI confirms the action was taken (or reports if it failed).

**The AI will never**:
- Execute actions without approval.
- Modify settings or positions automatically.
- Bypass the approval workflow through indirect prompts.

### 4.4 Action Types in Detail

**`highlight_section`**: Dims all UI panels except the specified section. Useful for focusing the user's attention on a specific panel (chart, order book, watchlist). Uses SECTION_SELECTORS to identify sections.

**`highlight_candles`**: Emphasizes a specific range of candles by index or time range. Used for pointing out patterns, divergence zones, or key price action areas.

**`highlight_region`**: Highlights a rectangular region defined by time and price coordinates. Best for marking support/resistance zones, supply/demand areas, or consolidation ranges.

**`highlight_chart_area`**: Highlights a percentage-defined area of the chart canvas. More abstract than coordinates.

**`highlight_contextual_zone`** (v0.29.0+): Highlights based on **analysis context**, not explicit chart coordinates. Takes `zone_type` (13 types: breakout, breakdown, support_test, resistance_test, bullish_divergence, bearish_divergence, consolidation, reversal_candles, volume_spike, trend_push, accumulation, distribution, recent_action), `direction` (bullish/bearish/neutral), and `candle_count`. The frontend resolves the exact chart region based on recent price action relative to the zone type.

**`add_drawing`**: Places a drawing tool on the chart using data-space coordinates. Supports all 40+ tools listed in `LMView_Drawing_Tools.md`. Requires `tool` name, `anchor_points` (array of {time, price}), and optional `params` (style, color, etc.).

### 4.5 Walkthrough Mode (Multi-Action Guided Analysis)

> *Available since v0.29.0, redesigned in v0.32.0*

Walkthrough Mode (previously Tour Mode) extends Interact Mode with **structured, multi-action analysis steps**. When you ask a complex question like "Analyze BTC and identify key patterns," the AI produces a walkthrough — a step-by-step plan where each step may involve **multiple simultaneous chart actions** (e.g., add RSI + highlight oversold zone + draw trendline — all in one step).

#### Walkthrough Lifecycle

1. **AI plans** — The AI produces a structured walkthrough with N steps, each step having:
   - An **explanation** (what to look for, why it matters)
   - An **array of actions** (draw tool, highlight, add indicator, navigate)
   - A **keep_effects flag** — if false, chart state resets between steps
2. **Auto-execution** — Each step's actions execute automatically one by one with a brief pause between them for visual clarity.
3. **Step reset** — If `keep_effects=false`, all AI-created drawings and highlights are cleared before the next step executes.
4. **Recap** — After the final step, the AI shows a **recap** summarizing what was discovered and what the user should watch for.
5. **Post-walkthrough options**:
   - **Replay** — Re-run the walkthrough from the beginning to follow along manually.
   - **Keep** — Preserve the final chart state (drawings and highlights remain).
   - **Revert** — Clear all AI modifications and return the chart to its pre-walkthrough state.

#### Walkthrough Examples

| Query | Typical Steps | Actions per Step |
|---|---|---|
| "Analyze BTC support/resistance" | 3-4 steps: zoom to daily → draw S/R lines → highlight reaction zones → note key levels | 1-2 per step |
| "Is there a bullish divergence?" | 3 steps: add RSI → highlight low swings on price + RSI → draw divergence lines | 2-3 per step |
| "Show me the market structure" | 4 steps: switch to 4H → draw trendlines → mark swing highs/lows → highlight consolidation | 1-2 per step |

#### Available Walkthrough Actions (35+ tools)

The AI can propose **any of 35+ typed actions** during walkthrough steps. Key categories:

| Category | Tools | Example Usage |
|---|---|---|
| **Chart config** | set_timeframe, set_chart_type, set_symbol, set_visible_range | "Switch to 4H BTC" |
| **Indicators** | add_indicator, remove_indicator, toggle_indicator, configure_indicator | "Add RSI with period 14" |
| **Drawing** | draw_tool, draw_trendline, create_annotation, clear_drawings, delete_drawing, set_drawing_color | "Draw trendline from high to low" |
| **Highlight** | highlight_region, highlight_chart_area, highlight_candles, highlight_contextual_zone, highlight_section | "Highlight the demand zone" |
| **Navigation** | zoom_chart, scroll_chart, scroll_chart_to_time, reset_chart_view, open_panel, close_panel, switch_panel_tab, switch_app_view, view_section | "Zoom in to the breakout" |
| **News** | open_news_popup | "Show related news" |
| **Replay** | enter_replay, export_chart | "Replay the last 24 hours" |

#### Thinking Indicator

During analysis, the AI shows a **thinking indicator** that cycles through the actual analysis steps being performed ("Analyzing indicators...", "Checking chart patterns...", "Checking market data..."). This gives visibility into the AI's analytical process.

#### Walkthrough vs Interact: Key Differences

| Aspect | Regular Interact | Walkthrough Mode |
|---|---|---|
| **Actions** | Single actions proposed one at a time | Multi-action steps, auto-executed |
| **Flow** | User-driven (ask → respond → ask) | AI-driven (plan → execute → recap) |
| **Chart state** | User manages | AI manages with step reset |
| **End state** | Continues indefinitely | Recap with Keep/Revert/Replay |

### 4.6 Limitations

- **Cannot propose trades.** No "buy" or "sell" actions are available.
- **Cannot modify positions or account settings.** Only chart/UI actions.
- **Output may be truncated** if the AI attempts to propose too many actions at once.
- **Tour is dynamically generated** and may not cover deeply advanced features. For advanced topics, users can ask specific questions.
- **Action parameters are validated** against an allowed list. Unrecognized parameters are rejected.

---

## 5. AI Model Selection

### 5.1 Tier System

Users can select from four model tiers in the Settings panel:

| Tier | Quality | Speed | Best For | Fallback |
|---|---|---|---|---|
| **Auto** (default) | Adaptive | Adaptive | Automatically selects best tier for the query | N/A |
| **Standard** | Good | Fast | Daily use, quick analysis | Falls through standard models |
| **Reserved** | Very good | Moderate | Complex analysis, deep reasoning | Falls to Standard if quota exceeded |
| **Benchmark** | Excellent | Slower | Detailed reports, multi-expert analysis | Falls through tiers |
| **None** | N/A | N/A | Disables AI features | — |

### 5.2 Model Options

Behind each tier is a specific model from the DashScope (Alibaba Cloud) API, Singapore region:

- **Standard Tier** (daily rotation): Qwen3.7-Plus (primary) → Qwen3.6-Plus → Qwen3.6-Flash → Qwen3.5-Plus (fallback).
- **Reserved Tier** (manual/premium): Qwen3.7-Max → QwQ-32B (reasoning model for complex multi-step) → DeepSeek-R1 (alternative reasoning).
- **Benchmark Tier** (automated eval): Qwen3.6-Max-Preview → Qwen3.5-Flash → Qwen2.5-72B-Instruct (baseline).
- **Mock/None**: Built-in mock provider returning canned responses (used when all API keys are exhausted or during development/testing).

### 5.3 Auto Mode

When the user selects "Auto," the AI automatically selects the appropriate tier based on:
1. **Query complexity** — Simple price questions use Standard; complex multi-faceted analysis uses Best.
2. **Recent API quota usage** — If API keys are approaching limits, downgrades tier to preserve functionality.
3. **Current load** — During peak usage, Standard tier is prioritized for responsiveness.

Auto mode is the default and recommended setting for most users.

---

## 6. Response Caching

The AI maintains a response cache to improve performance for common queries:

| Cache Policy | Detail |
|---|---|
| **Key** | SHA-256 hash of (message, symbol, timeframe, indicators, language, mode) |
| **TTL** | 30 seconds for price/market queries, 5 minutes for educational queries |
| **Max entries** | 100 |
| **Skipped** | Personalized (existing chat sessions), Interact mode actions |
| **Eviction** | LRU (Least Recently Used) |

The cache is checked before the AI graph executes. If a cached response exists and is fresh, it's returned immediately without invoking the LLM. This keeps repeated queries (like "What's the price of BTC?") very fast.

---

## 7. Financial Safety Protections

### 7.1 Always-Included Disclaimers

Every response that touches on market conditions includes appropriate disclaimers:

- "This is educational information, not financial advice."
- "Cryptocurrency trading carries significant risk of loss."
- "Past performance does not guarantee future results."
- "Technical analysis is one tool among many for decision-making."

### 7.2 Prohibited Behaviors

The AI is explicitly prevented from:

1. **Guaranteeing profits or returns** — No statement like "This setup guarantees 100% gains."
2. **Making specific price predictions** — No "BTC will hit $100,000 tomorrow."
3. **Suggesting specific trade sizes or leverage** — No "Buy $10,000 at 5× leverage."
4. **Claiming certainty** — No "This pattern always results in a breakout."
5. **FOMO/FUD language** — No "Don't miss this once-in-a-lifetime opportunity."
6. **Portfolio management instructions** — No "Sell all your alts and buy BTC."

### 7.3 Knowledge Boundary

The AI has a defined knowledge boundary and will decline to answer questions outside its domain:

- **In-scope**: Crypto technical analysis, LMView platform features, general crypto education, risk management concepts, DeFi analysis, on-chain analytics, market microstructure, correlation analysis, multi-timeframe analysis, order flow.
- **Out-of-scope**: Stock/commodity/forex advice, weather forecasts, creative writing, recipes, medical/legal/tax advice, price predictions, guaranteed returns.
- **Self-awareness**: When asked "Who are you?" or "What can you do?", the AI identifies as the LMView AI Assistant and lists its capabilities within the crypto analysis domain.

---

## 8. Bilingual Support Details

### Language Detection

The AI uses character-level detection:
- **Vietnamese detection**: If >2% of input characters are Vietnamese-specific (ô, ơ, ê, ư, ả, ẽ, ị, â, đ, ă, ê, ô, ơ, ư, ổ, ỗ, ộ, ậ, ẫ, ẩ, ễ, ể, ệ, ỷ, ỹ, ỵ, ặ, ắ, ằ, ẳ, ẵ), the AI responds in Vietnamese.
- **English detection**: Default. All other input assumes English response.

### Response Quality

- **Reasoning**: The AI works through analysis in English first (ensures quality).
- **Output**: For Vietnamese mode, the response body is entirely Vietnamese with no mixed English.
- **Terminology**: Standard Vietnamese trading terms are used consistently. See `Bilingual_Glossary.md` for the full term mapping.

---

## 9. Practical Usage Examples

### 9.1 Ask Mode Examples

**User**: "Is BTC in an uptrend on the 4H chart?"
**AI response**: "On the 4H chart, BTC is currently above both the 50 and 200 SMA (51,200 and 48,900 respectively), which is a bullish structure. ADX is at 28, indicating a trending market. The last pullback to 50,200 held above the 50 SMA, suggesting support is active. Key resistance is at 52,500 (recent swing high). The trend is intact as long as price stays above 49,500."

**User**: "Explain RSI divergence."
**AI response**: "RSI divergence occurs when price and RSI move in opposite directions. Bearish divergence: price makes a higher high, but RSI makes a lower high — momentum is weakening. Bullish divergence: price makes a lower low, but RSI makes a higher low — selling pressure is exhausting. Divergence is most reliable on higher timeframes (4H+). Always confirm with price action before acting."

### 9.2 Interact Mode Examples

**User**: "Add RSI to the chart."
**AI action**: Proposes `add_indicator(indicator="rsi", params={"period": 14})`. User approves. RSI is added to chart.

**User**: "Show me where support is."
**AI action**: Highlights the support zone with `highlight_region(time1: ..., time2: ..., price1: 49,500, price2: 50,000)` with text label "Key Support Zone (previous swing low + 200 SMA confluent)." User approves. Zone is highlighted.

**User**: "Walk me through the platform."
**AI action**: Creates a tour with steps explaining the left toolbar, chart area, right panel (watchlist → order book → trades → news), and settings. Each step includes navigation proposals requiring approval.

---

## 10. References

### AI Documentation
- `docs/ai/AI_ARCHITECTURE.md` — LangGraph pipeline, expert system architecture.
- `docs/ai/AI_PROVIDER_ROUTING.md` — Model selection and provider fallback logic.
- `docs/ai/AI_API_CONTRACTS.md` — API endpoints and request/response schemas.
- `docs/ai/AI_SECURITY.md` — Safety guardrails and scope gate implementation.
- `docs/ai/AI_EVALUATION.md` — Benchmark results and evaluation methodology.

### Knowledge Base Documents
- `docs/ai/knowledge_base/approved/LMView_General_Information.md` — Platform overview.
- `docs/ai/knowledge_base/approved/LMView_Technical_Indicators.md` — Complete indicator reference.
- `docs/ai/knowledge_base/approved/LMView_Drawing_Tools.md` — Drawing tools complete reference.
- `docs/ai/knowledge_base/approved/LMView_Function_Calling.md` — Interact mode function call documentation.
- `docs/ai/knowledge_base/approved/Technical_Analysis.md` — Technical analysis methodology.
- `docs/ai/knowledge_base/approved/Risk_Management_Frameworks.md` — Position sizing and risk management.
- `docs/ai/knowledge_base/approved/Bilingual_Glossary.md` — English/Vietnamese term mapping.

### System Documentation
- `docs/system/02-serving-layer.md` — Backend API serving layer.
- `docs/system/05-ai-service.md` — AI service container architecture.
- `docs/system/12-deployment.md` — Deployment and scaling details.
- `docs/system/13-caveats.md` — Known system limitations affecting AI responses.

---

## Appendix A — JSON Tool Call Blueprints

Every Interact mode action must conform to one of the following JSON structures.
Parameters are mandatory unless marked "optional".

### `add_indicator`

```json
{
  "action_type": "add_indicator",
  "params": {
    "indicator": "rsi",
    "indicator_name": "rsi",
    "params": {"period": 14}
  },
  "reason": "Show RSI to assess momentum divergence.",
  "requires_approval": true
}
```

Valid `indicator` values: `sma20`, `sma50`, `ema12`, `ema26`, `rsi`, `macd`,
`bollinger_bands`, `vwap`, `atr`, `volume_ma`, `stochastic`, `mfi`,
`ichimoku`, `supertrend`, `psar`.

**Use case**: User asks "show RSI" or "add MACD indicator".

---

### `draw_trendline`

```json
{
  "action_type": "draw_trendline",
  "params": {
    "from_time": 1718323200000,
    "from_price": 68500.0,
    "to_time": 1718582400000,
    "to_price": 64200.0,
    "color": "#00ff88",
    "style": "dashed"
  },
  "reason": "Connect swing lows to show ascending trendline support.",
  "requires_approval": true
}
```

Coordinates are epoch milliseconds × price. `style` is `solid`, `dashed`, or
`dotted` (optional, default `solid`). `color` is CSS hex (optional).

**Use case**: Identifying trend direction, drawing support/resistance lines.

---

### `draw_tool` (generic drawing tool selector)

```json
{
  "action_type": "draw_tool",
  "params": {
    "tool": "fibonacci",
    "points": [
      {"time": 1718323200000, "price": 68500},
      {"time": 1718582400000, "price": 62100}
    ],
    "text": "Fibonacci Retracement"
  },
  "reason": "Place Fibonacci retracement from swing low to swing high.",
  "requires_approval": true
}
```

`tool` enum: `trendline`, `fibonacci`, `rectangle`, `cursor`. The frontend
maps these to the appropriate drawing tool. `points` is an array of anchor
coordinates. `text` is optional label.

**Use case**: Complex drawing tools that need a generic interface.

---

### `highlight_candles`

```json
{
  "action_type": "highlight_candles",
  "params": {
    "start_time": 1718323200000,
    "end_time": 1718582400000,
    "label": "Bearish Engulfing",
    "message": "Wide-range bearish candle closing near low — selling pressure"
  },
  "reason": "Highlight bearish engulfing pattern at resistance.",
  "requires_approval": false
}
```

Use _time bounds_ (epoch ms) OR _index bounds_ (`from_index`/`to_index`), not
both. `message` is optional, shown as tooltip.

**Use case**: Pointing out specific candle patterns, reversal zones.

---

### `highlight_contextual_zone`

```json
{
  "action_type": "highlight_contextual_zone",
  "params": {
    "zone_type": "breakout",
    "direction": "bullish",
    "label": "Resistance Breakout",
    "message": "Price broke above $65,000 resistance with volume — watch for retest",
    "candle_count": 8
  },
  "reason": "Mark the breakout zone for user attention.",
  "requires_approval": false
}
```

Zone types: `breakout`, `breakdown`, `support_test`, `resistance_test`,
`bullish_divergence`, `bearish_divergence`, `consolidation`,
`reversal_candles`, `volume_spike`, `trend_push`, `accumulation`,
`distribution`, `recent_action`. The frontend resolves exact chart
coordinates from the zone type + recent price data.

**Use case**: Analysis-driven zone highlighting when precise coordinates
aren't available.

---

### `set_timeframe`

```json
{
  "action_type": "set_timeframe",
  "params": {"timeframe": "4h"},
  "reason": "Switch to 4H to assess the medium-term trend.",
  "requires_approval": true
}
```

Valid timeframes: `1s`, `1m`, `5m`, `15m`, `1h`, `4h`, `1d`, `1w`.

**Use case**: Multi-timeframe analysis, zooming in/out.

---

### `highlight_section`

```json
{
  "action_type": "highlight_section",
  "params": {
    "target": "orderBook",
    "section_id": "orderBook",
    "message": "Watch the bid-ask spread here for liquidation clusters"
  },
  "reason": "Guide user to the Order Book panel.",
  "requires_approval": false
}
```

Common `target` values: `chart`, `orderBook`, `watchlist`, `tradeTape`,
`news`, `screener`, `aiHelper`, `settings`.

**Use case**: Platform guidance, directing user attention to specific panels.

---

### `set_visible_range`

```json
{
  "action_type": "set_visible_range",
  "params": {
    "from_timestamp": 1718140800000,
    "to_timestamp": 1718755200000
  },
  "reason": "Zoom out to show the full consolidation range.",
  "requires_approval": true
}
```

Timestamps are epoch milliseconds. Used to programmatically zoom the chart.

**Use case**: Setting context for a multi-swing analysis.

---

### `set_chart_type`

```json
{
  "action_type": "set_chart_type",
  "params": {"chart_type": "heikinAshi"},
  "reason": "Switch to Heikin-Ashi to smooth out noise and see trend direction clearly.",
  "requires_approval": true
}
```

Valid chart types: `candles`, `bars`, `line`, `area`, `heikinAshi`, `renko`.

**Use case**: Changing chart type for clearer trend visualization.

---

### `remove_indicator`

```json
{
  "action_type": "remove_indicator",
  "params": {"indicator": "bollinger_bands", "indicator_name": "bollinger_bands"},
  "reason": "Remove Bollinger Bands to declutter the chart.",
  "requires_approval": true
}
```

Accepts either `indicator` or `indicator_name`. Same valid values as
`add_indicator`.

**Use case**: Cleaning up chart after analysis is complete.

---

### `create_annotation`

```json
{
  "action_type": "create_annotation",
  "params": {
    "time": 1718323200000,
    "price": 65000,
    "text": "Key resistance — 3 touches"
  },
  "reason": "Mark significant resistance level with note.",
  "requires_approval": true
}
```

`price` is optional (if omitted, annotation places at candle body center).
`text` is limited to 200 characters.

**Use case**: Adding price labels, marking key levels.

---

### `switch_panel_tab` (deprecated — use `highlight_section`)

Legacy. Do not use. Prefer `highlight_section` to guide the user to a panel.
