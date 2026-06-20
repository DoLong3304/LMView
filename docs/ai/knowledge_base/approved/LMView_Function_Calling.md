# LMView Function Calling — Interact Mode API

> **Document Type**: Function Calling Reference
> **Audience**: AI Assistant (Interact mode)
> **Version**: 0.25.42+

---

## Overview

LMView Interact mode allows the AI assistant to propose safe UI actions. All actions require explicit user approval before execution. This document defines the complete set of supported function calls, their parameters, usage scenarios, and examples.

**Safety Principle**: No action modifies data, executes trades, or changes settings without user consent. All actions are UI-only and reversible.

---

## Function Calling Format

The AI uses standard JSON-RPC-style function calls:

```json
{
  "function": "function_name",
  "parameters": {
    "param1": "value1",
    "param2": "value2"
  }
}
```

The AI receives tool definitions and should generate calls matching those schemas.

---

## Available Functions

### 1. AddIndicator

Add a technical indicator to the chart.

```json
{
  "function": "AddIndicator",
  "parameters": {
    "indicator": "string",       // Required: Indicator name (see Indicator Reference)
    "symbol": "string",          // Optional: Symbol (defaults to current)
    "timeframe": "string",       // Optional: Timeframe (defaults to current)
    "exchange": "string",        // Optional: Exchange (defaults to current)
    "config": {                  // Optional: Indicator-specific configuration
      "period": number,
      "color": string,
      "lineWidth": number,
      // ... other indicator-specific params
    }
  }
}
```

**Indicator Names** (case-insensitive):
- `sma`, `ema`, `rsi`, `macd`, `bb` (Bollinger Bands), `vwap`
- `volume`, `volumeMa`
- `atr`, `stochastic`, `mfi`
- `ichimoku`, `supertrend`, `psar`

**Examples**:
```json
{"function": "AddIndicator", "parameters": {"indicator": "rsi", "config": {"period": 14}}}
{"function": "AddIndicator", "parameters": {"indicator": "sma50"}}
```

**Warnings**:
- Adding duplicate indicator types with different periods is allowed.
- Indicator visibility persists across sessions.

---

### 2. RemoveIndicator

Remove an indicator from the chart.

```json
{
  "function": "RemoveIndicator",
  "parameters": {
    "indicator": "string",     // Required: Indicator name or ID
    "symbol": "string",        // Optional: Symbol (defaults to current)
    "timeframe": "string"      // Optional: Timeframe (defaults to current)
  }
}
```

**Examples**:
```json
{"function": "RemoveIndicator", "parameters": {"indicator": "rsi"}}
```

---

### 3. SetChartType

Change the chart visualization type.

```json
{
  "function": "SetChartType",
  "parameters": {
    "type": "string",      // Required: Chart type
    "settings": {          // Optional: Type-specific settings
      // Renko
      "brickSizeType": "fixed" | "atr",
      "fixedBrickSize": number,
      "atrPeriod": number,
      "renkoWicks": boolean,

      // Line Break
      "lookback": number,

      // Kagi
      "reversalPercent": number,
      "kagiUseClose": boolean
    }
  }
}
```

**Chart Types**:
- `candles` — Standard candlestick (default)
- `bars` — OHLC bars
- `line` — Close line
- `area` — Filled area
- `heikinAshi` — Heikin-Ashi smoothed candles
- `renko` — Renko bricks
- `lineBreak` — Line Break chart
- `kagi` — Kagi lines
- `pointFigure` — Point & Figure

**Examples**:
```json
{"function": "SetChartType", "parameters": {"type": "renko", "settings": {"brickSizeType": "fixed", "fixedBrickSize": 10}}}
```

---

### 4. SetTimeframe

Switch to a different timeframe.

```json
{
  "function": "SetTimeframe",
  "parameters": {
    "timeframe": "string"  // Required: One of 1s, 1m, 5m, 15m, 1h, 4h, 1d, 1w
  }
}
```

**Examples**:
```json
{"function": "SetTimeframe", "parameters": {"timeframe": "4h"}}
```

**Warnings**:
- Lower timeframes (1s, 1m) may have higher CPU/network usage.
- Some indicators require minimum candle count; switching may temporarily hide them.

---

### 5. SetSymbol

Change the currently viewed symbol.

```json
{
  "function": "SetSymbol",
  "parameters": {
    "symbol": "string",      // Required: Trading pair (e.g., BTCUSDT)
    "exchange": "string"     // Optional: Exchange (default: binance)
  }
}
```

**Examples**:
```json
{"function": "SetSymbol", "parameters": {"symbol": "ETHUSDT"}}
```

**Warnings**:
- Symbol must be in the exchange's active trading pairs.
- Chart resets drawing tools on symbol change.

---

### 6. NavigateTo

Navigate to a different panel or view.

```json
{
  "function": "NavigateTo",
  "parameters": {
    "panel": "string"  // Required: Target panel name
  }
}
```

**Panel Names**:
- `chart` — Main chart view (default)
- `orderbook` — Order book depth panel
- `trades` — Recent trades panel
- `watchlist` — Watchlist sidebar
- `screener` — Screener page
- `news` — News panel
- `settings` — Settings modal
- `ai` — AI assistant panel

**Examples**:
```json
{"function": "NavigateTo", "parameters": {"panel": "orderbook"}}
```

---

### 7. ShowDrawingTool

Select a drawing tool from the toolbar.

```json
{
  "function": "ShowDrawingTool",
  "parameters": {
    "tool": "string",       // Required: Drawing tool name
    "settings": {           // Optional: Tool-specific defaults
      "color": string,
      "lineWidth": number,
      // ... tool-specific params
    }
  }
}
```

**Tool Names** (see Drawing Tools Reference for full list):
- `trendline`, `horizontal`, `vertical`, `ray`
- `fibRetracement`, `fibExtension`
- `rectangle`, `triangle`, `arrow`
- `text`, `note`
- `ruler`, `riskReward`
- `longPosition`, `shortPosition`
- `gannFan`, `pitchfork`, `elliottWave`
- ... and more (40+ total)

**Examples**:
```json
{"function": "ShowDrawingTool", "parameters": {"tool": "fibRetracement"}}
```

---

### 8. DrawOnChart

Place a drawing directly on the chart at specified coordinates.

```json
{
  "function": "DrawOnChart",
  "parameters": {
    "tool": "string",        // Required: Drawing tool name
    "points": [              // Required: Array of data-space points
      {
        "time": number,      // Unix timestamp in seconds
        "price": number      // Price value
      }
    ],
    "settings": {            // Optional: Drawing appearance
      "color": string,
      "lineWidth": number
    }
  }
}
```

**Examples**:
```json
{
  "function": "DrawOnChart",
  "parameters": {
    "tool": "trendline",
    "points": [
      {"time": 1700000000, "price": 50000},
      {"time": 1700003600, "price": 51000}
    ]
  }
}
```

**Notes**:
- The AI must calculate data-space coordinates from chart context.
- Use current symbol and timeframe to determine time scale.

---

### 9. ClearDrawings

Remove all drawings from the chart.

```json
{
  "function": "ClearDrawings",
  "parameters": {
    "symbol": "string",      // Optional: Symbol (default: current)
    "timeframe": "string"    // Optional: Timeframe (default: current)
  }
}
```

**Examples**:
```json
{"function": "ClearDrawings", "parameters": {}}
```

**Warnings**:
- This action is irreversible without undo (if undo history is enabled).
- Affects all drawings on the current chart.

---

### 10. ToggleIndicatorVisibility

Show or hide an indicator without removing it.

```json
{
  "function": "ToggleIndicatorVisibility",
  "parameters": {
    "indicator": "string",   // Required: Indicator name
    "visible": boolean,      // Required: true to show, false to hide
    "symbol": "string",      // Optional: Symbol (default: current)
    "timeframe": "string"    // Optional: Timeframe (default: current)
  }
}
```

**Examples**:
```json
{"function": "ToggleIndicatorVisibility", "parameters": {"indicator": "sma20", "visible": false}}
```

---

### 11. UpdateIndicatorConfig

Modify an indicator's parameters.

```json
{
  "function": "UpdateIndicatorConfig",
  "parameters": {
    "indicator": "string",   // Required: Indicator name
    "config": {              // Required: Configuration updates
      "period": number,
      "color": string,
      "lineWidth": number,
      // ... indicator-specific params
    },
    "symbol": "string",      // Optional: Symbol (default: current)
    "timeframe": "string"    // Optional: Timeframe (default: current)
  }
}
```

**Examples**:
```json
{
  "function": "UpdateIndicatorConfig",
  "parameters": {
    "indicator": "bb",
    "config": {"multiplier": 2.5}
  }
}
```

---

### 12. AddToWatchlist

Add a symbol to the user's watchlist.

```json
{
  "function": "AddToWatchlist",
  "parameters": {
    "symbol": "string",      // Required: Symbol to add
    "exchange": "string"     // Optional: Exchange (default: binance)
  }
}
```

**Examples**:
```json
{"function": "AddToWatchlist", "parameters": {"symbol": "ETHUSDT"}}
```

**Warnings**:
- Duplicate symbols are ignored.
- Watchlist is persisted to user settings.

---

### 13. RemoveFromWatchlist

Remove a symbol from the watchlist.

```json
{
  "function": "RemoveFromWatchlist",
  "parameters": {
    "symbol": "string"       // Required: Symbol to remove
  }
}
```

**Examples**:
```json
{"function": "RemoveFromWatchlist", "parameters": {"symbol": "BTCUSDT"}}
```

---

### 14. StartGuidedTour

Begin a guided tour highlighting specific UI elements.

```json
{
  "function": "StartGuidedTour",
  "parameters": {
    "tourId": "string",      // Required: Tour identifier
    "step": number           // Optional: Start at specific step (default: 0)
  }
}
```

**Available Tours**:
- `onboarding` — First-time user tour
- `indicators` — How to add and configure indicators
- `drawing` — Drawing tools tutorial
- `ai-ask` — Using Ask mode
- `ai-interact` — Using Interact mode

**Examples**:
```json
{"function": "StartGuidedTour", "parameters": {"tourId": "indicators"}}
```

---

### 15. ShowTooltip

Display a temporary tooltip or notification.

```json
{
  "function": "ShowTooltip",
  "parameters": {
    "message": "string",     // Required: Message text
    "type": "string",        // Optional: "info" | "success" | "warning" | "error"
    "duration": number       // Optional: Display duration in ms (default: 3000)
  }
}
```

**Examples**:
```json
{"function": "ShowTooltip", "parameters": {"message": "RSI added to chart", "type": "success"}}
```

---

### 16. CaptureChartSnapshot

Capture the current chart state for AI context or sharing.

```json
{
  "function": "CaptureChartSnapshot",
  "parameters": {
    "includeDrawings": boolean,   // Optional: Include drawings (default: true)
    "includeIndicators": boolean  // Optional: Include indicators (default: true)
  }
}
```

**Returns**: A snapshot ID that can be referenced in subsequent analysis.

**Examples**:
```json
{"function": "CaptureChartSnapshot", "parameters": {}}
```

**Note**: This function is primarily for internal AI context building; user doesn't see the result directly.

---

## Function Response Format

When the AI proposes an action, the system returns:

```json
{
  "actionId": "uuid",
  "function": "function_name",
  "parameters": { ... },
  "status": "proposed",  // or "approved", "rejected", "executed", "failed"
  "message": "Human-readable description",
  "requiresApproval": true,
  "preview": { ... }  // Optional: Preview of what will change
}
```

The user sees a card with "Approve" and "Reject" buttons.

---

## Execution Flow

1. **AI proposes** → `POST /api/ai/action/propose`
2. **System validates** → Returns `actionId`, `preview`
3. **User sees card** → Approve or Reject
4. **If approve** → `POST /api/ai/action/approve/{actionId}`
5. **If reject** → `POST /api/ai/action/reject/{actionId}`
6. **Execution** → System performs action, updates UI
7. **Confirmation** → WebSocket event broadcast: `{"type": "action_executed", "actionId": "...", "status": "success"}`

---

## Error Handling

Common errors:

| Error Code | Meaning | Likely Cause |
|------------|---------|--------------|
| `INVALID_PARAMETERS` | Parameter validation failed | Wrong type, missing required field |
| `UNSUPPORTED_FUNCTION` | Function not recognized | Typo in function name |
| `SYMBOL_NOT_FOUND` | Symbol doesn't exist | Invalid trading pair |
| `INDICATOR_UNAVAILABLE` | Indicator not supported | Wrong indicator name |
| `EXECUTION_FAILED` | Action failed during execution | Backend error, network issue |
| `NOT_AUTHORIZED` | User lacks permission | Session expired or insufficient rights |

AI should explain errors to user in plain language.

---

## Safety & Approval Rules

**Always Requires Approval**:
- All functions except `ShowTooltip` and `CaptureChartSnapshot` require user approval.
- The AI must never claim it can execute actions directly.

**No-Go Zones** (functions that will be rejected):
- Trade execution (no such function exists)
- Withdrawal/transfer functions (don't exist)
- Settings changes that affect other users (impossible)
- Direct database access (impossible)

**Idempotency**:
- Adding the same indicator twice returns the existing one (no duplicate).
- Removing a non-existent indicator is a no-op (treated as success).
- Setting chart type to current type is a no-op.

---

## Context Awareness

When calling functions, the AI should be aware of:
- Current `symbol`, `timeframe`, `exchange` from chat context
- Already active indicators (check before proposing adds)
- Available drawing tools (tool must exist)
- User's language preference (messages in response should match)

The AI can query current state by:
- Asking the user (e.g., "What indicators are currently on your chart?")
- Including a context request in its analysis (the system may provide snapshot data)

---

## Best Practices for AI

1. **Check before adding** — If RSI already active with period 14, don't add another unless user requests different period.
2. **Explain what you're doing** — "I'll add a 50-period SMA to your BTC/USDT 1h chart."
3. **Handle errors gracefully** — If symbol not found, suggest valid alternatives from the watchlist.
4. **Respect approval flow** — Never say "I've added..." until user approves.
5. **Use minimal parameters** — Only specify what's needed; let system use defaults.
6. **Prefer specific over generic** — Use `sma50` not `sma` with period 50 (both work, but be explicit).

---

## Versioning

This specification is valid for LMView version `0.25.42+`. Future versions may add new functions or deprecate existing ones. The AI should check `/api/ai/functions` (hypothetical) for runtime-available function definitions if implemented.

---

## Appendix: Full Schema Summary

```typescript
// IndicatorConfig
interface IndicatorConfig {
  period?: number;
  color?: string;          // Hex color
  lineWidth?: number;
  type?: string;          // For composite indicators (MACD, Stochastic)
  overbought?: number;    // For RSI, Stochastic
  oversold?: number;      // For RSI, Stochastic
  multiplier?: number;    // For Bollinger Bands, Supertrend
  fastPeriod?: number;    // MACD
  slowPeriod?: number;    // MACD
  signalPeriod?: number;  // MACD
  // ... indicator-specific
}

// ChartSettings
interface ChartSettings {
  brickSizeType?: "fixed" | "atr";
  fixedBrickSize?: number;
  atrPeriod?: number;
  renkoWicks?: boolean;
  lookback?: number;
  reversalPercent?: number;
  kagiUseClose?: boolean;
}

// DrawingPoint
interface DrawingPoint {
  time: number;    // Unix seconds
  price: number;
}

// DrawingSettings
interface DrawingSettings {
  color?: string;
  lineWidth?: number;
  lineStyle?: "solid" | "dashed" | "dotted";
  fill?: boolean;
  fillColor?: string;
  fillOpacity?: number;
  // Tool-specific fields...
}
```

---

## References

- **Drawing Tools Reference**: `LMView_Drawing_Tools.md`
- **Technical Indicators Reference**: `LMView_Technical_Indicators.md`
- **System Architecture**: `LMView_System_Internal.md`
