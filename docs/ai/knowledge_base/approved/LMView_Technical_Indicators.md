# LMView Technical Indicators — Complete Reference

> **Document Type**: Technical Reference
> **Audience**: AI Assistant, Traders
> **Version**: 0.25.42+
> **Source Formulas**: Standard academic definitions; LMView implementation verified against `backend/services/indicator_service.py`

---

## Introduction

LMView provides **16+ technical indicators** computed in real-time by Apache Flink or derived on-demand from Redis candle history. This document details each indicator's formula, parameters, interpretation, and LMView-specific behavior.

### Indicator Categories

| Category | Indicators |
|----------|------------|
| **Trend** | SMA, EMA, Ichimoku Cloud, Supertrend, Parabolic SAR |
| **Momentum** | RSI, MACD, Stochastic, MFI |
| **Volatility** | Bollinger Bands, ATR |
| **Volume** | Volume, Volume MA, VWAP |

---

## General Notes

### Data Sources

Indicators come from two sources:

1. **Flink Precomputed** — Real-time from stream (default, <500ms latency)
2. **Redis-Derived** — On-demand from kline history when Flink data unavailable/stale

**Response metadata** includes:
```json
{
  "source": "flink_precomputed" | "redis_derived" | "unavailable",
  "freshness_seconds": 0.3,
  "is_stale": false,
  "is_fallback": false
}
```

### Series Support

Some indicators support full time series via `/api/indicators/{symbol}/series` endpoint (returns array of `{timestamp, value}`). Others only provide latest snapshot.

### Parameter Customization

Default parameters can be overridden when adding indicators via UI or Interact mode. Allowed ranges are documented per indicator.

---

## Indicator Reference

### 1. SMA (Simple Moving Average)

**Category**: Trend  
**Series Support**: Yes  
**Default Parameters**: `period=20` (SMA 20), `period=50` (SMA 50)  
**LMView Aliases**: `sma20`, `sma50`

#### Purpose
Smooths price data by averaging closing prices over N periods. Identifies trend direction and dynamic support/resistance.

#### Formula
```
SMA(n) = (P₁ + P₂ + ... + Pₙ) / n
```
where Pᵢ = closing price at bar i, n = period.

#### Interpretation
- Price above SMA → bullish trend
- Price below SMA → bearish trend
- SMA crossovers (fast vs slow) signal trend changes
- SMA acts as dynamic support (in uptrend) or resistance (in downtrend)

#### LMView Implementation
- Flink: Uses cumulative sum with rolling window
- Redis-derived: Same calculation from kline history
- Required candles: `n`

#### Trading Signals
| Signal | Condition | Strength |
|--------|-----------|----------|
| Bullish | Price crosses above SMA | Moderate |
| Bearish | Price crosses below SMA | Moderate |
| Strong trend | Price far from SMA (>2×ATR) | High |
| Consolidation | Price oscillates around SMA | Neutral |

#### Usage Tips
- Combine multiple SMAs (e.g., 20 + 50) for golden/death cross signals
- SMA 200 is commonly used for long-term trend but not pre-enabled in LMView; can be added as custom SMA 200

---

### 2. EMA (Exponential Moving Average)

**Category**: Trend  
**Series Support**: Yes  
**Default Parameters**: `period=12` (EMA 12), `period=26` (EMA 26)  
**LMView Aliases**: `ema12`, `ema26`

#### Purpose
Like SMA but gives more weight to recent prices, reacting faster to price changes.

#### Formula
```
Multiplier = 2 / (n + 1)
EMA₁ = SMA(first n prices)
EMAᵢ = (Pᵢ × Multiplier) + (EMAᵢ₋₁ × (1 - Multiplier))
```

#### Interpretation
- EMA more responsive than SMA; better for short-term signals
- EMA-SMA cross indicates momentum shifts
- Widely used in MACD construction (EMA 12 and EMA 26)

#### LMView Implementation
- Flink and Redis-derived use identical EMA formula
- First EMA value seeded with SMA of first n prices
- Required candles: `n`

#### Trading Signals
| Signal | Condition |
|--------|-----------|
| Bullish momentum | EMA rising, price above EMA |
| Bearish momentum | EMA falling, price below EMA |
| Crossover | Fast EMA crosses slow EMA (12 vs 26) |

---

### 3. RSI (Relative Strength Index)

**Category**: Momentum  
**Series Support**: Yes  
**Default Parameters**: `period=14`, `overbought=70`, `oversold=30`  
**LMView Alias**: `rsi`, `rsi14`

#### Purpose
Measures speed and magnitude of recent price changes to identify overbought/oversold conditions.

#### Formula (Wilder's Method — Used by LMView)
```
RS = Average Gain / Average Loss (over period)
RSI = 100 - (100 / (1 + RS))
```
Where Average Gain/Loss uses Wilder's smoothing (not SMA):
```
AvgGain₀ = SMA(first period gains)
AvgLoss₀ = SMA(first period losses)
AvgGainᵢ = ((AvgGainᵢ₋₁ × (n-1)) + current_gain) / n
AvgLossᵢ = ((AvgLossᵢ₋₁ × (n-1)) + current_loss) / n
```

**Note**: LMView Flink uses Wilder's RSI. Some Spark batch implementations use SMA smoothing, causing minor discrepancies.

#### Scale
0 to 100

#### Interpretation
- **Overbought**: RSI > 70 → potential reversal down
- **Oversold**: RSI < 30 → potential reversal up
- **Neutral**: 30-70 → no strong signal
- **Divergence**: Price makes new high but RSI makes lower high → bearish reversal signal

#### LMView Details
- Required candles: `period + 1` (15 for default 14)
- Available from Flink precomputed or Redis-derived fallback
- No RSI series support for values < 0 or > 100 (clamped)

#### Trading Signals
| Signal | Condition | Confirmation |
|--------|-----------|--------------|
| Overbought | RSI > 70 | Wait for bearish divergence or cross back below 70 |
| Oversold | RSI < 30 | Wait for bullish divergence or cross back above 30 |
| Bullish divergence | Price lower low, RSI higher low | Strong reversal signal |
| Bearish divergence | Price higher high, RSI lower high | Strong reversal signal |
| Centerline cross | RSI crosses 50 | Momentum shift |

---

### 4. MACD (Moving Average Convergence Divergence)

**Category**: Momentum  
**Series Support**: Yes (returns three series: `macd`, `macd_signal`, `macd_histogram`)  
**Default Parameters**: `fastPeriod=12`, `slowPeriod=26`, `signalPeriod=9`  
**LMView Aliases**: `macd`

#### Purpose
Measures relationship between two EMAs; shows momentum changes and trend direction.

#### Formula
```
MACD Line = EMA(12) - EMA(26)
Signal Line = EMA(9) of MACD Line
Histogram = MACD Line - Signal Line
```

#### Scale
Price units (not normalized)

#### Interpretation
- **MACD Line > 0** → bullish (12EMA > 26EMA)
- **MACD Line crosses Signal Line** → trade signal
  - Bullish: MACD crosses above signal
  - Bearish: MACD crosses below signal
- **Histogram** bars show momentum strength; shrinking histogram → convergence, reversal pending

#### LMView Details
- Series returns: `macd`, `macd_signal`, `macd_histogram`
- Required candles: 26 + 9 = 35
- All series aligned to slow EMA timestamp

#### Trading Signals
| Signal | Condition |
|--------|-----------|
| Bullish | MACD line crosses above signal line |
| Bearish | MACD line crosses below signal line |
| Bullish momentum | Histogram bars increasing positive |
| Bearish momentum | Histogram bars decreasing negative |
| Overbought/bearish divergence | MACD makes lower high while price makes higher high |

---

### 5. Bollinger Bands (BB)

**Category**: Volatility  
**Series Support**: Yes (returns `bb_middle`, `bb_upper`, `bb_lower`, `bb_width`)  
**Default Parameters**: `period=20`, `std_dev=2`  
**LMView Aliases**: `bb`, `bollinger_bands`

#### Purpose
Measure volatility and potential overbought/oversold conditions via standard deviation channels.

#### Formula
```
Middle Band = SMA(20)
Upper Band = SMA(20) + (2 × Standard Deviation)
Lower Band = SMA(20) - (2 × Standard Deviation)
Width = (Upper - Lower) / Middle
```

**Important**: LMView uses **population standard deviation** (divide by n, not n-1) for consistency with TradingView.

#### Interpretation
- **Squeeze**: Band width contracts → low volatility → impending breakout
- **Touch upper band** → overbought (not alone a sell signal)
- **Touch lower band** → oversold (not alone a buy signal)
- **Price outside bands** → strong trend (not necessarily reversal)

#### LMView Details
- Required candles: 20
- Returns: `bb_middle`, `bb_upper`, `bb_lower`, `bb_width`
- Band width normalized as percentage of middle band

#### Trading Signals
| Signal | Condition |
|--------|-----------|
| Volatility expansion | Band width increasing |
| Volatility contraction | Band width decreasing (squeeze) |
| Potential reversal | Price touches upper band + bearish candle pattern |
| Strong trend | Price rides upper band (uptrend) or lower band (downtrend) |

---

### 6. VWAP (Volume-Weighted Average Price)

**Category**: Volume  
**Series Support**: No (latest snapshot only)  
**Default Parameters**: None  
**LMView Alias**: `vwap`

#### Purpose
Intraday benchmark representing average price weighted by volume. Institutional reference.

#### Formula
```
VWAP = Σ(Price × Volume) / Σ(Volume)
```
Calculated from session open (usually 00:00 UTC) to current bar.

#### Interpretation
- **Above VWAP** → bullish intraday bias
- **Below VWAP** → bearish intraday bias
- **VWAP as support/resistance** → Price often reverts to VWAP
- **High volume near VWAP** → strong acceptance at that level

#### LMView Details
- Computed from Flink stream using cumulative volume
- Resets daily (session-based)
- No series support (only latest value)
- Not available on higher timeframes that span multiple sessions? (verify)

#### Trading Signals
| Signal | Condition |
|--------|-----------|
| Bullish | Price > VWAP, VWAP rising |
| Bearish | Price < VWAP, VWAP falling |
| Rejection | Price touches VWAP and bounces |
| Breakthrough | Price moves through VWAP with volume |

---

### 7. Volume MA (Volume Moving Average)

**Category**: Volume  
**Series Support**: Yes  
**Default Parameters**: `period=20`  
**LMView Aliases**: `volumeMa`, `volume_ma`, `volume_sma20`

#### Purpose
Smooth volume data to identify unusual spikes or trends.

#### Formula
```
Volume MA(n) = SMA of volume over n periods
```

#### Interpretation
- **Volume spike > 2×MA** → significant interest (breakout/breakdown)
- **Volume declining** → lack of conviction
- **Volume rising with price** → healthy trend
- **Volume diverging** (price up, volume down) → weakness

#### LMView Details
- Required candles: 20
- Uses same SMA calculation as price SMA
- Series supported

#### Trading Signals
| Signal | Condition |
|--------|-----------|
| Breakout confirmation | Volume > 2× MA + price breakout |
| Exhaustion | Volume spike after strong move + price reversal |
| Trend health | Volume above MA during trend continuation |

---

### 8. ATR (Average True Range)

**Category**: Volatility  
**Series Support**: Yes  
**Default Parameters**: `period=14`  
**LMView Aliases**: `atr`, `atr14`

#### Purpose
Measure market volatility; average range of price movement.

#### Formula
```
True Range = max(
  high - low,
  |high - previous_close|,
  |low - previous_close|
)
ATR = Wilder's smoothing of True Range (like RSI)
```

**Wilder's smoothing**:
```
ATR₁ = SMA(first period TR)
ATRᵢ = ((ATRᵢ₋₁ × (n-1)) + current_TR) / n
```

#### Scale
Price units (same as underlying)

#### Interpretation
- **High ATR** → high volatility, wider stops needed
- **Low ATR** → consolidation, tighter stops possible
- **ATR expansion** → volatility increasing (often before breakouts)
- **ATR contraction** → volatility decreasing (consolidation)

#### LMView Details
- Required candles: `period + 1` = 15
- Flink uses Wilder's method; Redis-derived uses same
- Series supported

#### Trading Applications
- Position sizing: Risk = 2×ATR → stop distance
- Stop placement: Set stops at 1.5-3×ATR from entry
- Breakout detection: Price move > ATR signals momentum

---

### 9. Stochastic Oscillator

**Category**: Momentum  
**Series Support**: No (latest snapshot only as of current implementation)  
**Default Parameters**: `k=14`, `d=3`, `overbought=80`, `oversold=20`  
**LMView Alias**: `stochastic`

#### Purpose
Compare closing price to price range over period; identify momentum and potential reversals.

#### Formula (Fast Stochastic — Used by LMView)
```
%K = (Current Close - Lowest Low) / (Highest High - Lowest Low) × 100
  where Lowest Low = lowest low over k periods
        Highest High = highest high over k periods

%D = SMA(3) of %K
```

#### Scale
0 to 100

#### Interpretation
- **Overbought**: %K > 80
- **Oversold**: %K < 20
- **Bullish signal**: %K crosses above %D while below 20
- **Bearish signal**: %K crosses below %D while above 80
- **Divergence**: Price vs Stochastic divergence → reversal warning

#### LMView Details
- Currently precomputed by Flink
- Series support may be added in future
- Required candles: 14 + 3 = 17

---

### 10. MFI (Money Flow Index)

**Category**: Momentum  
**Series Support**: No (latest snapshot only)  
**Default Parameters**: `period=14`, `overbought=80`, `oversold=20`  
**LMView Alias**: `mfi`

#### Purpose
Volume-weighted RSI; combines price and volume to identify money flow.

#### Formula
```
Typical Price = (High + Low + Close) / 3
Money Flow = Typical Price × Volume

Positive MF = Sum of Money Flow where TP > previous TP
Negative MF = Sum of Money Flow where TP < previous TP

MFI = 100 - (100 / (1 + Positive MF / Negative MF))
```
Uses Wilder's smoothing for averages.

#### Scale
0 to 100

#### Interpretation
- **MFI > 80** → overbought, potential selling pressure
- **MFI < 20** → oversold, potential buying pressure
- **MFI vs RSI**: MFI includes volume, often more reliable but slower

#### LMView Details
- Required candles: 14
- Precomputed by Flink

---

### 11. Ichimoku Cloud (Ichimoku Kinko Hyo)

**Category**: Trend  
**Series Support**: No (latest snapshot with multiple lines)  
**Default Parameters**: `conversion=9`, `base=26`, `span=52`, `displacement=26`  
**LMView Alias**: `ichimoku`

#### Purpose
Comprehensive indicator showing support/resistance, trend direction, and momentum.

#### Formulas

```
Tenkan-sen (Conversion Line) = (9-period High + 9-period Low) / 2
Kijun-sen (Base Line) = (26-period High + 26-period Low) / 2
Senkou Span A (Leading Span A) = (Tenkan + Kijun) / 2, displaced 26 periods forward
Senkou Span B (Leading Span B) = (52-period High + 52-period Low) / 2, displaced 26 periods forward
Chikou Span (Lagging Span) = Current Close, displaced 26 periods backward
```

#### Components

| Line | Meaning |
|------|---------|
| Tenkan-sen | Short-term momentum (9-period midpoint) |
| Kijun-sen | Medium-term trend; dynamic support/resistance |
| Senkou Span A | Leading span 1 (forms cloud upper) |
| Senkou Span B | Leading span 2 (forms cloud lower) |
| Cloud (Kumo) | Area between Span A and Span B → support/resistance zone |
| Chikou Span | Lagging line; confirms trends |

#### Interpretation

- **Price above Cloud** → Bullish trend
- **Price below Cloud** → Bearish trend
- **Cloud color**: Span A > Span B = green (bullish cloud); red = bearish
- **Cloud thick** → strong support/resistance; thin cloud = weak
- **Tenkan > Kijun** → short-term bullish
- **Price crossing Cloud** → potential trend change
- **Chikou above/below price** → confirms trend direction

#### LMView Details
- Precomputed by Flink
- Returns multiple values: `ichimoku_conversion`, `ichimoku_base`, `ichimoku_span_a`, `ichimoku_span_b`
- Displacement handled by frontend rendering (shift spans forward/backward)
- Required candles: 52

---

### 12. Supertrend

**Category**: Trend  
**Series Support**: No (latest snapshot only)  
**Default Parameters**: `period=10`, `multiplier=3`  
**LMView Alias**: `supertrend`

#### Purpose
Trend-following indicator showing support (uptrend) or resistance (downtrend) lines.

#### Formula

```
HL2 = (High + Low) / 2
ATR = Average True Range (period)

Upper Band = HL2 + (multiplier × ATR)
Lower Band = HL2 - (multiplier × ATR)

Supertrend = 
  if Close > previous Upper Band:
    Lower Band (trend up)
  elif Close < previous Lower Band:
    Upper Band (trend down)
  else:
    previous Supertrend value
```

The indicator flips to opposite band when price crosses it.

#### Interpretation
- **Green line below price** → Uptrend (buy signal when price crosses above)
- **Red line above price** → Downtrend (sell signal when price crosses below)
- **Line position** → dynamic stop-loss level
- **Flip** → trend reversal signal

#### LMView Details
- Uses ATR internally (period 10 default)
- Precomputed by Flink
- Required candles: period + buffer

#### Trading Signals
| Signal | Condition |
|--------|-----------|
| Buy / uptrend start | Price crosses above Supertrend (line turns green below) |
| Sell / downtrend start | Price crosses below Supertrend (line turns red above) |
| Trailing stop | Keep stop below Supertrend in uptrend (green) |

---

### 13. Parabolic SAR (Stop and Reverse)

**Category**: Trend  
**Series Support**: No (latest snapshot only)  
**Default Parameters**: `step=0.02`, `max_step=0.2`  
**LMView Alias**: `psar`

#### Purpose
Trend indicator that provides potential stop-loss levels and reversal signals.

#### Formula

```
SAR = previous SAR + (step × (EP - previous SAR))
with acceleration factor (AF) increasing by step each bar until reaching max_step
EP = Extreme Point (highest high in uptrend or lowest low in downtrend)
```

The SAR dots appear below price in uptrends (bullish) and above price in downtrends (bearish). When price crosses SAR, trend reverses and SAR flips to opposite side.

#### Interpretation
- **Dots below price** → Uptrend
- **Dots above price** → Downtrend
- **Dots flip** → Trend reversal signal
- **Dots distance** → Wider gaps = stronger momentum; tight dots = consolidation

#### LMView Details
- Precomputed by Flink
- Standard step=0.02, max=0.2 (TradingView defaults)

#### Trading Signals
| Signal | Condition |
|--------|-----------|
| Uptrend start | SAR dots flip below price |
| Downtrend start | SAR dots flip above price |
| Exit signal | Price touches SAR dots (stop hit) |
| Reversal warning | Dots converging (AF increasing) |

---

### 14. Volume (Raw)

**Category**: Volume  
**Series Support**: Yes  
**Default Parameters**: None  
**LMView Alias**: `volume`

#### Purpose
Shows trading activity volume per candle.

#### Data
- Volume value = total base asset units traded during candle period
- Colored bars: green if candle closed up, red if closed down

#### Interpretation
- **High volume** → strong conviction, confirms moves
- **Low volume** → weak move, potential false breakout
- **Volume profile** → Identify high-volume nodes (value areas)
- **Volume spikes** → News events, liquidation events

#### LMView Details
- Available directly from kline data
- Series supported
- No computation required

---

## Indicator Comparison Table

| Indicator | Category | Series | Default Params | Required Candles | Source |
|-----------|----------|--------|----------------|------------------|--------|
| SMA 20 | Trend | Yes | period=20 | 20 | Flink/Redis |
| SMA 50 | Trend | Yes | period=50 | 50 | Flink/Redis |
| EMA 12 | Trend | Yes | period=12 | 12 | Flink/Redis |
| EMA 26 | Trend | Yes | period=26 | 26 | Flink/Redis |
| RSI | Momentum | Yes | period=14 | 15 | Flink/Redis |
| MACD | Momentum | Yes (3 series) | 12/26/9 | 35 | Flink/Redis |
| Bollinger Bands | Volatility | Yes (4 series) | period=20, std=2 | 20 | Flink/Redis |
| VWAP | Volume | No | — | session | Flink |
| Volume MA | Volume | Yes | period=20 | 20 | Flink/Redis |
| Stochastic | Momentum | No | k=14, d=3 | 17 | Flink |
| MFI | Momentum | No | period=14 | 14 | Flink |
| ATR | Volatility | Yes | period=14 | 15 | Flink/Redis |
| Ichimoku | Trend | No | conv=9, base=26, span=52 | 52 | Flink |
| Supertrend | Trend | No | period=10, mult=3 | ~10 | Flink |
| Parabolic SAR | Trend | No | step=0.02, max=0.2 | ~25 | Flink |

---

## Combining Indicators

### Classic Combinations

1. **Trend + Momentum**:
   - SMA 50 + RSI
   - Price above SMA 50 + RSI > 50 → bullish
   - RSI divergence with price warns of trend weakness

2. **Volatility + Trend**:
   - Bollinger Bands + SMA
   - Bollinger Squeeze → anticipate breakout
   - Price at upper band + uptrend → strong bullish

3. **MACD + Signal**:
   - MACD line cross + histogram expansion
   - Confirm with volume spike

4. **Ichimoku + Price**:
   - Price above Cloud + Tenkan > Kijun → strong uptrend
   - Cloud acts as support

### Confluence is Key

No single indicator is reliable. Look for multiple confirmations:
- Trend (SMA/EMA/Ichimoku) aligned
- Momentum (RSI/MACD) supporting
- Volume confirming
- Price action pattern (chart pattern or Fibonacci level)

---

## Common Pitfalls

| Pitfall | Why It's Bad | Better Approach |
|---------|--------------|-----------------|
| Relying on single indicator | High false signal rate | Use 2-3 confirming indicators |
| Trading overbought/oversold blindly | Markets can stay extreme | Wait for actual reversal signals |
| Using default RSI 70/30 in strong trends | Levels need adjustment | Use 80/20 in strong bull markets |
| Ignoring volume | Volume confirms or negates moves | Always check volume with price action |
| Chasing every divergence | Divergence can persist long | Wait for price confirmation |

---

## LMView-Specific Notes

### Freshness & Fallback

When indicators are computed from Redis-derived fallback (not Flink), the `freshness` object includes:
```json
{
  "source": "redis_derived",
  "is_fallback": true,
  "warnings": ["Indicators computed from Redis kline history"]
}
```

The AI should mention this if it affects confidence.

### Indicator Unavailability

If an indicator is not yet computed by Flink and Redis lacks sufficient history, the API returns `null` for that indicator. The `indicator_summary` endpoint's `available` array lists what's currently accessible.

### Custom Periods

Users can request custom periods (e.g., SMA 200) via Interact mode:
```json
{"function": "AddIndicator", "parameters": {"indicator": "sma", "config": {"period": 200}}}
```
LMView will compute it on-demand from Redis kline history if not precomputed.

---

## Formula Summary (Quick Reference)

| Indicator | Core Formula |
|-----------|--------------|
| SMA | Sum(close, n) / n |
| EMA | `EMA = (close × 2/(n+1)) + EMA_prev × (1 - 2/(n+1))` |
| RSI | `100 - (100 / (1 + WilderAvgGain/WilderAvgLoss))` |
| MACD | `EMA12 - EMA26`, signal = EMA9(MACD) |
| BB | `SMA ± (2 × population_stddev)` |
| ATR | Wilder's average of `max(high-low, |high-prevClose|, |low-prevClose|)` |
| Stochastic | `%K = (close - min(low, n)) / (max(high, n) - min(low, n)) × 100` |
| MFI | `100 - (100 / (1 + sum(PositiveMF)/sum(NegativeMF)))` |
| VWAP | `Σ(price×volume) / Σ(volume)` (session cumulative) |

---

## References

- **Function Calling**: `LMView_Function_Calling.md`
- **Drawing Tools**: `LMView_Drawing_Tools.md`
- **System Architecture**: `LMView_System_Internal.md`
- **Backend Implementation**: `backend/services/indicator_service.py`
