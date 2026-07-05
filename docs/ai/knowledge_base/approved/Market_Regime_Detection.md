# Market Regime Detection — Complete Guide

> **Document Type**: Educational Reference
> **Audience**: AI Assistant, End Users
> **Version**: 0.27.0+
> **Domain**: Technical Analysis, Trading Methodology

---

## Table of Contents

1. What is a Market Regime?
2. Why Regime Detection Matters
3. Trending vs Ranging Regimes
   - 3.1 Characteristics of Each Regime
   - 3.2 Why Misidentification Is Dangerous
4. Volatility Regimes (ATR-Based)
   - 4.1 Low Volatility (Compression)
   - 4.2 Expanding Volatility (Acceleration)
   - 4.3 High Volatility (Unstable)
   - 4.4 ATR Percentile Ranking
5. ADX — The Primary Trend Strength Tool
   - 5.1 Calculation Overview
   - 5.2 Threshold Values
   - 5.3 Directional Movement (+DI / −DI)
   - 5.4 ADX Rising vs ADX Falling
   - 5.5 ADX Limitations
6. Chop Index — Quantifying Ranging Markets
   - 6.1 Calculation
   - 6.2 Threshold Values
   - 6.3 Combining with ADX
7. Efficient Frontier / Fractal Efficiency Ratio
8. Moving Average Slope and Angle
9. Bollinger Band Width — Volatility Contraction/Expansion
10. Volume-Based Regime Confirmation
     - 10.1 Volume Confirming Trend
     - 10.2 Volume Preceding Breakout
     - 10.3 Volume Exhaustion
11. Regime Detection Scorecard
12. Trading Strategies by Regime
     - 12.1 Trending: Trend-Following
     - 12.2 Ranging: Mean Reversion
     - 12.3 Low Volatility: Breakout Anticipation
     - 12.4 High Volatility: Wide Stops, Reduced Size
13. Regime Change Warning Signals
14. Practical Analysis Workflow
15. Important Caveats and Limitations
16. References and Further Reading

---

## 1. What Is a Market Regime?

A market regime describes the **prevailing behavior** of price in a given timeframe: how it moves, how it responds to support/resistance, and which strategies are most effective.

Four primary regimes:

| Regime | Behavior | Strategy Preference |
|---|---|---|
| **Trending** | Price makes persistent directional moves | Trend-following (MA cross, MACD) |
| **Ranging** | Price oscillates between defined levels | Mean reversion (RSI, Bollinger Bands) |
| **Low volatility** | Tight compression, breakout pending | Breakout anticipation (squeeze setups) |
| **High volatility** | Wide swings, unstable structure | Caution, reduced position size |

**Key insight**: Most traders fail because they apply trend-following strategies in ranging markets and mean-reversion strategies in trending markets. The regime determines the strategy, not the other way around.

---

## 2. Why Regime Detection Matters

Using the wrong strategy for the current regime causes consistent losses:

| Regime | Wrong Strategy Applied | Result |
|---|---|---|
| Trending | Mean reversion (fading extremes) | Stop loss hit repeatedly as trend continues |
| Ranging | Trend following (buying breakouts) | False breakouts → losses |
| Low volatility | Any directional strategy | Small moves, no profit direction |
| High volatility | Standard position sizing | Account blow-up from oversized losses |

**The financial cost**: A 20-pip trend-following strategy that works well in a trending market (win rate 60%) becomes a losing strategy in a ranging market (win rate 30%). The same data, the same chart — only the regime changed.

**For the AI**: When a user describes losses or frustration, start by asking about the market regime they're trading. Explaining regime misalignment is often more useful than suggesting different indicators.

---

## 3. Trending vs Ranging Regimes

### 3.1 Characteristics of Each Regime

| Feature | Trending | Ranging (Sideways) |
|---|---|---|
| **Price structure** | Higher highs + higher lows (up); lower highs + lower lows (down) | Horizontal moves between support and resistance |
| **MA alignment** | Price stays on one side of MA; shorter MAs above longer MAs (up) | Price crosses back and forth across MAs; MAs flat |
| **Bollinger Bands** | Bands slope and expand in trend direction | Bands horizontal, contracts |
| **Volume** | Rising volume confirms trend direction | Volume fades at extremes, spikes at support/resistance |
| **RSI** | Spends extended time above 60 (up) or below 40 (down) | Oscillates between 30–70 regularly |
| **ADX** | Above 25 | Below 20 |
| **Chop Index** | Below 40 | Above 60 |
| **Pullback behavior** | Pullbacks are shallow and brief | Reversals are deep and reach opposite extremes |

### 3.2 Why Misidentification Is Dangerous

**Example**: A trader sees a price rising 5% and assumes a trend, buying the breakout. But the overall structure is ranging (price at the top of the 5-month range). They buy at resistance, get stopped out when price reverses back to support.

**Cost**: Entry at top of range + stop loss extra wide (assuming trend continuation) = potentially multiple R losses.

**Prevention**: Always check the higher timeframe first. A 1H uptrend means nothing if the daily is clearly ranging between ATH and support. The daily regime dominates.

---

## 4. Volatility Regimes (ATR-Based)

The Average True Range (ATR) measures the average price range over a period (typically 14). It tells you how much the price typically moves — not direction.

### 4.1 Low Volatility (Compression)

**Signs**:
- ATR at or near its 50-period low
- Bollinger Bands narrowing (Band Width near low)
- Active month range < 50% of average monthly range

**Meaning**: The market is compressing. A breakout is coming. The longer the compression, the larger the eventual move.

**Trading approach**:
- Place breakout orders above and below the compression range.
- Reduce position size (breakout may go either direction).
- Wait for volume confirmation before adding to the winning side.

**Common pattern**: "Bollinger Band Squeeze" — narrowest bands in 6 months → explosive move within 1–3 bars.

### 4.2 Expanding Volatility (Acceleration)

**Signs**:
- ATR rising for 5+ consecutive periods
- Price making large directional candles
- Gaps starting to appear between closes and opens

**Meaning**: A trend is gaining momentum. The gap between current price and moving averages may widen.

**Trading approach**:
- Add to positions in trend direction.
- Trail stops more aggressively (ATR-based, e.g., 2× ATR).
- Do NOT fade the move. In accelerating volatility, reversals are brief and deep.

### 4.3 High Volatility (Unstable)

**Signs**:
- ATR at or above the 95th percentile of its 100-period range
- Price has moved 2–3× the average daily range in consecutive days
- Slippage increases, spreads widen

**Meaning**: The market is in a state of unusual activity (news event, liquidation cascade, black swan).

**Trading approach**:
- **Reduce position size dramatically.** Normal stop distances will get hit by noise.
- Consider staying on the sidelines until conditions normalize.
- If trading, use wider stops (3–4× ATR) and smaller size (25–50% of normal).

**Warning indicators**:
- Spread widening on major pairs (BTC spread > 0.02% is unusual).
- Orders executing with unexpected slippage.
- Intraday range exceeding the average daily range by 2×.

### 4.4 ATR Percentile Ranking

A more precise volatility assessment: rank current ATR relative to its 100-period history.

| Percentile | Regime | Recommendation |
|---|---|---|
| > 95% | Extreme volatility | Reduce size, widen stops, or stand aside |
| 75–95% | High volatility | Use normal size with wider stops, favor trending strategies |
| 25–75% | Normal volatility | Standard setups with standard parameters |
| 5–25% | Low volatility | Anticipate breakout, reduce trend strategies |
| < 5% | Extreme compression | Breakout imminent; use small size with wide target |

---

## 5. ADX — The Primary Trend Strength Tool

The Average Directional Index (ADX), developed by J. Welles Wilder, measures trend strength without indicating direction.

### 5.1 Calculation Overview

ADX is derived from two directional indicators:
- **+DI** (Positive Directional Indicator): Measures upward price movement strength.
- **−DI** (Negative Directional Indicator): Measures downward price movement strength.

ADX = Smoothed average of the difference between +DI and −DI, divided by their sum.

Default period: 14.

### 5.2 Threshold Values

| ADX Value | Regime | Description |
|---|---|---|
| 0–20 | Weak/no trend | Ranging. Use mean-reversion strategies. False signals high. |
| 20–25 | Transitional | Market deciding direction. Breakout or rollover imminent. |
| 25–40 | Trending | Strong trend. Trend-following strategies work best. |
| 40–60 | Very strong trend | Extended move. Momentum is strong but move may be mature. |
| 60+ | Extremely strong trend | Rare. Often occurs during mania/capitulation. Reversal imminent. |

**Important nuance**: A high ADX (50+) does NOT mean "the trend is more reliable." It means the trend is **extreme**. The higher ADX goes above 40, the more likely a trend reversal or sharp mean reversion becomes.

### 5.3 Directional Movement (+DI / −DI)

ADX alone doesn't tell direction. Use +DI and −DI:

| Condition | Interpretation |
|---|---|
| **+DI > −DI, ADX > 25** | Bullish trend in progress |
| **−DI > +DI, ADX > 25** | Bearish trend in progress |
| **+DI crosses above −DI, ADX rising** | Bullish trend starting |
| **−DI crosses above +DI, ADX rising** | Bearish trend starting |
| **+DI and −DI wide apart, ADX high** | Strong trend, both directions diverging |
| **+DI and −DI converging, ADX falling** | Trend weakening, possible range |

### 5.4 ADX Rising vs ADX Falling

| ADX Direction | Meaning | Action |
|---|---|---|
| **Rising from below 20 to above 25** | New trend beginning | Enter in direction of +DI / −DI |
| **Rising from 25 to 40+** | Trend accelerating | Hold, add on pullbacks |
| **Falling from 40+ to below 30** | Trend weakening | Take partial profits, tighten stops |
| **Flat below 20** | Ranging/no trend | Don't trade trend strategies |
| **Flat above 40** | Strong sustained trend | Hold with trailing stop |

### 5.5 ADX Limitations

- **ADX is a lagging indicator.** It confirms a trend that already started. By the time ADX crosses 25, price may have already moved significantly.
- **ADX cannot predict direction.** It only measures strength. +DI / −DI crossovers are needed for direction.
- **ADX gives false signals in choppy markets.** Price can make strong directional swings within a range that spike ADX above 25.
- **High ADX does not predict trend continuation.** Some of the best reversals happen when ADX is at extreme levels.

---

## 6. Chop Index — Quantifying Ranging Markets

The Chop Index (sometimes called "Choppiness Index") was developed by E.W. Dreiss and measures whether the market is trending or ranging.

### 6.1 Calculation

Chop Index uses the True Range and the price range over a lookback period (typically 14). It ranges from 0 to 100:

```
Chop = 100 × log10(Σ(ATR) / (High - Low)) / log10(N)
```

Where N is the lookback period. Higher values = more choppy/ranging. Lower values = trending.

### 6.2 Threshold Values

| Value | Regime | Strategy |
|---|---|---|
| > 60 | Choppy / ranging | Use mean-reversion, avoid trend strategies |
| 40–60 | Transitional / neutral | Reduce size, wait for clearer signal |
| < 40 | Trending | Favor trend-following, avoid fading moves |

### 6.3 Combining with ADX

The combination of ADX and Chop Index gives a more complete picture:

| ADX | Chop | Interpretation |
|---|---|---|
| > 25 | < 40 | Strong trend. Both indicators agree. Trade direction. |
| < 20 | > 60 | Strong range. Both indicators agree. Trade mean-reversion. |
| > 25 | > 60 | Divergence. Price moving but choppy. Possibly a trend in a wide range. Caution. |
| < 20 | < 40 | Divergence. Low ADX says no trend, but Chop says not choppy. Usually implies a transitional period. |

---

## 7. Efficient Frontier / Fractal Efficiency Ratio

The Fractal Efficiency Ratio (FER) was developed by John Ehlers to measure how efficiently price moves in one direction.

**Calculation**: (Net change over N periods) ÷ (Sum of absolute changes over N periods)

- **FER near +1.0** → Price moving efficiently upward (trending)
- **FER near −1.0** → Price moving efficiently downward (trending)
- **FER near 0.0** → Price going nowhere (ranging)

**Parameters**: Typical period = 10–20 (crypto) or 5–10 (forex/stock).

**Use case**: Enter trades when |FER| > 0.5 and exit when |FER| falls below 0.2. This filters out choppy periods and keeps you in strong directional moves.

---

## 8. Moving Average Slope and Angle

The slope of a moving average (especially the 50 and 200 SMA) is a simple but powerful regime indicator.

**Calculation**: Average slope over N periods.

```
Slope = (Current MA − MA N periods ago) / N
Angle = arctan(Slope) × (180 / π)
```

| MA Slope | Regime | Meaning |
|---|---|---|
| **Steeply rising (> 45°)** | Strong uptrend | Momentum-driven, pullbacks likely bought |
| **Gradually rising (10°–45°)** | Normal uptrend | Healthy, sustainable rise |
| **Flat (−10° to +10°)** | Ranging / consolidating | No directional edge |
| **Gradually falling (−10° to −45°)** | Normal downtrend | Healthy, sustainable decline |
| **Steeply falling (< −45°)** | Strong downtrend | Momentum-driven, bounces likely sold |

**Best MA for slope**: 50-period SMA gives medium-term regime. 200-period SMA gives long-term trend. 20-period EMA gives short-term momentum.

---

## 9. Bollinger Band Width — Volatility Contraction/Expansion

Bollinger Band Width is the distance between the upper and lower bands as a percentage of the middle band:

```
Band Width = (Upper − Lower) / Middle × 100
```

| Band Width | Regime | Meaning |
|---|---|---|
| At 6-month low | Compressed | Low volatility, breakout pending |
| Expanding from low | Breakout started | Trend beginning, direction = side broken |
| At 6-month high | Extended | High volatility, move may be exhausting |
| Contracting from high | Trend ending | Volatility declining, potential range |

**The "Squeeze" pattern** (popularized by John Bollinger):
- Band Width drops to its lowest level in 6+ months.
- Market is at its calmest.
- A directional explosion typically follows within 1–7 bars.
- The direction is unknown until it happens.

---

## 10. Volume-Based Regime Confirmation

### 10.1 Volume Confirming Trend

| Price Action | Volume | Interpretation |
|---|---|---|
| Rising | Rising | Healthy uptrend. Participants confirming. |
| Rising | Falling | Weakening uptrend. Lack of conviction. |
| Falling | Rising | Healthy downtrend. Participants confirming. |
| Falling | Falling | Weakening downtrend. Selling exhaustion. |

### 10.2 Volume Preceding Breakout

Before major breakouts:
- Volume often falls to very low levels during the compression.
- The breakout bar should have volume 2–3× the 20-period average.
- If breakout has low volume → high probability of false breakout (trap).

### 10.3 Volume Exhaustion

Near trend ends:
- Volume spikes to extreme levels (3–5× average).
- But the next bar fails to extend the move.
- This is climax volume → trend likely reversing.

---

## 11. Regime Detection Scorecard

A quick reference tool combining all indicators:

| Indicator | Trending Up | Trending Down | Ranging | Compressing |
|---|---|---|---|---|
| **Price structure** | HH + HL | LH + LL | Horizontal | Tight range |
| **MA alignment** | 20 > 50 > 200 | 20 < 50 < 200 | Crosses / flat | Flat |
| **MA slope (50)** | > +15° | < −15° | −10° to +10° | Near 0 |
| **ADX** | > 25 | > 25 | < 20 | < 20 |
| **Chop Index** | < 40 | < 40 | > 60 | > 60 |
| **RSI** | > 60 | < 40 | 30–70 | 40–60 |
| **Band Width** | Expanding | Expanding | Stable | At low |
| **Volume** | Confirming | Confirming | Fading | Low |
| **Strategy** | Buy dips | Sell rallies | Fade | Wait |

If 6+ indicators agree → high confidence regime identification.
If 3–5 agree → moderate confidence. Use smaller size.
If < 3 agree → regime unclear. Stand aside.

---

## 12. Trading Strategies by Regime

### 12.1 Trending: Trend-Following

**Tools**: MA cross, MACD, Parabolic SAR, ADX > 25.
**Entry**: On pullback to MA (20 EMA / 50 SMA) with +DI > −DI.
**Stop**: Below the most recent swing low (uptrend) or MA by 1.5× ATR.
**Take profit**: Trailing stop at 2× ATR, or when ADX turns down from > 40.
**Add**: On the weakest pullback (lowest volume rejection).

### 12.2 Ranging: Mean Reversion

**Tools**: RSI (30/70), Stochastic (20/80), Bollinger Bands.
**Entry**: At support with RSI < 30 (long) or at resistance with RSI > 70 (short).
**Stop**: Beyond the range boundary by 1× ATR.
**Take profit**: Mid-range or opposite extreme.
**Key rule**: Take profits quickly. Ranges do not trend. Expect price to revert.

### 12.3 Low Volatility: Breakout Anticipation

**Tools**: Bollinger Band Width, ATR percentile, volatility expansion.
**Entry**: Place pending orders above/below the compression range. Enter on the first breakout candle that closes outside the range with volume > 2× average.
**Stop**: Inside the compression range.
**Take profit**: 2–3× the range height (measured move).

### 12.4 High Volatility: Wide Stops, Reduced Size

**Tools**: ATR, spread monitoring.
**Entry**: Only with clear directional edge (ADX > 40 + volume confirmation).
**Position size**: 25–50% of normal.
**Stop**: 3–4× ATR.
**Take profit**: 1:1 risk-reward (shorter targets because moves are extreme).

---

## 13. Regime Change Warning Signals

The most critical skill in regime detection is spotting regime transitions early:

### Trending → Ranging
- ADX peaks above 40 and starts declining
- Price fails to make new highs/lows despite +DI/−DI still aligned
- MA slope flattens
- Volume drops as price approaches previous extreme

### Ranging → Trending
- ADX rises above 20–25
- Price closes outside the range with volume
- MA slope begins to angle in the breakout direction
- ATR expands from a low

### Low Volatility → High Volatility
- ATR jumps from sub-10th percentile to above 50th percentile within a few bars
- Band Width expands rapidly
- Consecutive bars exceed the prior 20-bar average range

---

## 14. Practical Analysis Workflow

Follow this step-by-step when analyzing a chart from a regime perspective:

### Step 1: Identify the Dominant Regime
1. Look at the **200-period MA** — is sloped up, down, or flat? This is your primary trend.
2. Check **ADX** on the trading timeframe:
   - > 25 → trending
   - < 20 → ranging
3. Cross-check with **Chop Index**:
   - > 60 → ranging
   - < 40 → trending
4. Verify with **price structure** (HH/HL vs LH/LL vs horizontal).

### Step 2: Check Volatility Regime
1. Where is ATR in its 100-period range?
2. Is Bollinger Band Width near its lows?
3. Is volume normal, elevated, or declining?

### Step 3: Align Strategy with Regime
- Trending → Trend-following strategy.
- Ranging → Mean-reversion strategy.
- Low vol → Breakout anticipation.
- High vol → Caution, reduced size.

### Step 4: Identify Regime Transition Risk
1. Is ADX falling from a high → trend weakening?
2. Is ADX rising from low → potential trend starting?
3. Is Band Width at extremes → compression or expansion imminent?

### Step 5: State Your Confidence
- **High**: 6+ indicators align on regime. Clear setup.
- **Moderate**: 3–5 indicators agree. Use smaller position.
- **Low**: Indeterminate. No clear edge. Wait.

### AI Response Template
When a user asks about a trade or setup, structure the response around regime:

> "On the 4H chart, the current regime appears to be [trending/ranging/transitional]. ADX is at [value], suggesting [trend/range]. ATR is at the [percentile] percentile of its 100-period range, indicating [low/normal/high] volatility. Given this regime, [recommended strategy] would be more appropriate than [strategy to avoid]. Key risk is [regime change signal]."

---

## 15. Important Caveats and Limitations

1. **Regime detection is probabilistic, not deterministic.** No indicator is 100% accurate.
2. **Different timeframes may show different regimes.** A 1H uptrend within a daily range means you're in a pullback within a range, not a trend. Always check the higher timeframe.
3. **Regimes can change suddenly.** A news event can switch the market from ranging to high-volatility trending in minutes.
4. **ADX and Chop Index are lagging.** They confirm regimes after they've started. You will miss the very beginning.
5. **These indicators work best when combined.** Using just one (e.g., ADX alone) leads to false identification.
6. **Crypto markets have different regime behavior.** Extended trending periods (bull/bear markets) are followed by prolonged ranging periods (accumulation/distribution). The transition between them can take weeks.
7. **During high-volatility regimes, all indicators become less reliable.** Slippage, spread widening, and rapid order book changes make execution difficult.
8. **The AI must not present regime detection as a trading recommendation.** Always frame as: "The technical structure suggests [regime], which historically favors [strategy]. However, regime can change without warning."

---

## 16. References and Further Reading

### Books
- *New Concepts in Technical Trading Systems* by J. Welles Wilder — Original ADX, RSI, and ATR development.
- *Technical Analysis of the Financial Markets* by John J. Murphy — Comprehensive overview of regime indicators.
- *Bollinger on Bollinger Bands* by John Bollinger — Band Width and squeeze patterns.
- *Cybernetic Analysis for Stocks and Futures* by John Ehlers — Fractal efficiency and adaptive market analysis.
- *Trading for a Living* by Alexander Elder — Triple-screen trading system (multi-timeframe regime approach).
- *The Best Trend Following Methods* by Bo Yoder — Trend identification and regime filtering.

### Trading Platforms
- **TradingView** — ADX, Chop Index, Band Width indicators built-in.
- **Sierra Chart** — Advanced volatility and market profile analysis.
- **Thinkorswim (TD Ameritrade)** — Studies scanner for ADX and ATR percentile.

### LMView-Specific
- `Technical_Analysis.md` — Individual indicator guides (RSI, MACD, Bollinger Bands).
- `Multi_Timeframe_Analysis.md` — Regime alignment across timeframes.
- `Order_Flow_Analysis.md` — Volume and delta to confirm regime.
