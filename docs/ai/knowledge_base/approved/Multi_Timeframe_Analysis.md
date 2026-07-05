# Multi-Timeframe Analysis — Complete Guide

> **Document Type**: Educational Reference
> **Audience**: AI Assistant, End Users
> **Version**: 0.27.0+
> **Domain**: Technical Analysis, Trading Methodology

---

## Table of Contents

1. Why Multi-Timeframe Analysis (MTFA)
2. The Top-Down Pyramid
3. Timeframe Hierarchy and Relationship
   - 3.1 Common Timeframe Sets
   - 3.2 The 1:4 Ratio Principle
4. Higher Timeframe (HTF) — The Primary Trend
5. Intermediate Timeframe (ITF) — The Secondary Move
6. Lower Timeframe (LTF) — Entry and Exit
7. Timeframe Alignment Signals
   - 7.1 All Three Aligned
   - 7.2 HTF Up, ITF Down, LTF Up
   - 7.3 HTF Down, ITF Up, LTF Down
   - 7.4 All Conflicting
   - 7.5 Other Alignment Patterns
8. Confluency Scoring
9. Common Multi-TF Setups
   - 9.1 Trend Continuation
   - 9.2 Breakout Trading
   - 9.3 Reversal Trading
   - 9.4 Pullback Entry (The Most Common Setup)
   - 9.5 Failure Swing / Tap and Reverse
10. Indicator Alignment Across Timeframes
     - 10.1 RSI Across Timeframes
     - 10.2 MACD Across Timeframes
     - 10.3 Moving Averages Across Timeframes
     - 10.4 Volume Across Timeframes
11. Divergence Across Timeframes
     - 11.1 LTF Divergence Within HTF Trend
     - 11.2 HTF Divergence
12. Timeframe Mismatch and Common Mistakes
13. MTFA in Crypto Markets
14. Practical Analysis Workflow
15. LMView-Specific Timeframe Handling
16. References and Further Reading

---

## 1. Why Multi-Timeframe Analysis (MTFA)

Single-timeframe analysis is inherently incomplete. A price action that looks like a strong breakout on the 5-minute chart may be nothing more than a minor retracement within a larger downtrend on the 4-hour chart. Looking at a single timeframe is like reading one paragraph of a book and guessing the plot.

Multi-timeframe analysis provides:
- **Context**: The higher timeframe tells you the dominant trend, so you're not fighting it.
- **Timing**: The lower timeframe tells you the optimal entry/exit within that trend.
- **Confirmation**: When multiple timeframes align, the trade has higher probability of success.
- **Filtering**: When timeframes conflict, you know to reduce size or skip the trade.

**Core principle**: Higher timeframes dominate lower timeframes. A 4-hour trend will overpower a 5-minute counter-trend move every time. Trade in the direction of the higher timeframe.

---

## 2. The Top-Down Pyramid

Start with the highest timeframe and work your way down. Never start with the chart you plan to trade — start one to two timeframes higher.

```
        Monthly / Weekly
              ↓
           Daily
              ↓
           4-Hour
              ↓
          1-Hour
              ↓
         15-Minute
              ↓
           5-Minute
              ↓
           1-Minute
```

**You must identify the direction and structure on EACH timeframe** before taking a trade on your execution timeframe.

**Analogy**: Think of the higher timeframe as the ocean tide (unidirectional, hours of movement) and the lower timeframe as the waves (back and forth, minutes of movement). Trade with the tide, use the waves for entry.

---

## 3. Timeframe Hierarchy and Relationship

### 3.1 Common Timeframe Sets

| Trading Style | HTF (Trend) | ITF (Setup) | LTF (Entry) |
|---|---|---|---|
| **Scalping** | 15m | 5m | 1m |
| **Intraday** | 1H | 15m | 5m |
| **Swing** | Daily | 4H | 1H |
| **Position** | Weekly | Daily | 4H |
| **Long-term** | Monthly | Weekly | Daily |

**Crypto-specific note**: Due to 24/7 trading, crypto moves can be compressed. Many swing traders use 4H as their HTF and 15m as LTF. The traditional "stock market" timeframe hierarchy (where weekends exist) is slightly different.

### 3.2 The 1:4 Ratio Principle

For meaningful analysis, each timeframe should be roughly **4×** the next lower one:

- 1D / 4H = 6× (acceptable)
- 4H / 1H = 4× (ideal)
- 1H / 15m = 4× (ideal)
- 15m / 5m = 3× (acceptable)
- 5m / 1m = 5× (acceptable)

If the ratio is too small (e.g., 5m → 3m), the timeframes are too similar and don't provide independent information. Aim for at least a 3× difference between each layer.

---

## 4. Higher Timeframe (HTF) — The Primary Trend

The HTF determines the dominant direction. Everything else is noise within this trend.

**What to analyze on HTF:**
1. **Trend direction** — Higher highs + higher lows (bull), lower highs + lower lows (bear), or horizontal (range).
2. **Key S/R levels** — Major support, resistance, previous swing highs/lows.
3. **Structure** — Is the trend mature (extended) or just starting?
4. **Volume** — Is volume confirming the HTF direction?
5. **Indicators on HTF** — RSI extreme, MACD direction, MA alignment.

**Typical checklist for HTF analysis:**
- [ ] 200-period MA slope → primary trend filter
- [ ] Price relative to 200 MA → above = bullish bias, below = bearish bias
- [ ] 50-period MA slope → medium-term trend
- [ ] Key swing high / low levels identified
- [ ] Major S/R zones drawn (daily/weekly pivots)
- [ ] RSI on HTF: is it extended (>70 or <30)?
- [ ] Volume profile: POC direction, VAH/VAL levels

**Decision**: Based on HTF, determine your **bias**. Long only if HTF is bullish. Short only if HTF is bearish. If HTF is ranging, be neutral and trade both sides.

---

## 5. Intermediate Timeframe (ITF) — The Secondary Move

The ITF shows the current run (or pullback) within the HTF trend. It's where you identify the **setup pattern**.

**What to analyze on ITF:**
1. **Pullback structure** — Is it a shallow dip (bull flag) or a deep retracement (potential reversal)?
2. **ITF trend direction** — Is it aligned with HTF or counter-trend?
3. **Pattern recognition** — Flags, wedges, triangles, head and shoulders.
4. **Candlestick patterns** — Engulfing, pin bars, inside bars at key levels.
5. **ITF indicators** — MACD crossing, RSI returning from extreme.

**Key insight**: The ITF is where most traders make mistakes. They see a strong ITF move and assume it's the HTF trend, ignoring the higher-level context. Always check the ITF against the HTF, not in isolation.

---

## 6. Lower Timeframe (LTF) — Entry and Exit

The LTF is your **execution** timeframe. It's where you fine-tune the entry, set stops, and manage the trade.

**What to analyze on LTF:**
1. **Entry trigger** — Specific candlestick pattern, LTF structure break, indicator signal.
2. **Stop placement** — Below the nearest swing low (long) or above the nearest swing high (short).
3. **Exit targets** — First target at ITF S/R, second target at HTF S/R.
4. **Timing** — Is the LTF structure showing a completion of the pullback (for trend entry) or exhaustion (for reversal)?

**LTF rules**:
- Do NOT trade against HTF direction, even if LTF looks attractive.
- LTF signals within HTF direction have higher win rate.
- LTF signals against HTF direction are counter-trend and should be taken only with clear confluence (e.g., HTF S/R level + LTF reversal pattern).

---

## 7. Timeframe Alignment Signals

### 7.1 All Three Aligned (Strongest Signal)

| Timeframe | Direction | Meaning |
|---|---|---|
| HTF | Up | Primary trend is bullish |
| ITF | Up | Secondary move aligns, pullback not yet started |
| LTF | Up | Price is in immediate uptrend |

**Outcome**: Strong trend, favorable risk/reward for long positions. Add to positions, hold through pullbacks.

**Action**: Look for LTF pullbacks to enter long. HTF targets can be extended.

### 7.2 HTF Up, ITF Down, LTF Up (Pullback in Uptrend)

| Timeframe | Direction | Meaning |
|---|---|---|
| HTF | Up | Primary trend bullish |
| ITF | Down | Pullback in progress |
| LTF | Up | LTF bounce within the pullback |

**Outcome**: This is the **ideal pullback entry** in a trend. The LTF bounce signals the pullback may be ending.

**Action**: Wait for ITF downtrend to show completion (ITF structure break, ITF RSI returning from 30, ITF MACD crossing up). Enter long on the next LTF pullback.

### 7.3 HTF Down, ITF Up, LTF Down (Bounce in Downtrend)

| Timeframe | Direction | Meaning |
|---|---|---|
| HTF | Down | Primary trend bearish |
| ITF | Up | Bounce/relief rally in progress |
| LTF | Down | LTF dip within the bounce |

**Outcome**: The mirror of 7.2. A counter-trend bounce that should be sold into.

**Action**: Wait for ITF bounce to show exhaustion (ITF RSI returning from 70, ITF MACD crossing down). Enter short on the next LTF bounce.

### 7.4 All Conflicting (Weak/No Signal)

| Timeframe | Direction |
|---|---|
| HTF | Up |
| ITF | Down |
| LTF | Up |

Wait, that's the same as 7.2. Let me clarify:

**All conflicting** means the trend is unclear — HTF ranging, ITF choppy, LTF erratic.

| Timeframe | Direction | Meaning |
|---|---|---|
| HTF | Sideways | No dominant bias |
| ITF | Sideways | No secondary move |
| LTF | Choppy | No clean signal |

**Outcome**: No edge. Trade only with clear HTF S/R levels and tight stops.

**Action**: Focus on mean-reversion at range extremes. Reduce size. Wait for HTF breakout to establish direction.

### 7.5 Other Alignment Patterns

| HTF | ITF | LTF | Interpretation | Strategy |
|---|---|---|---|---|
| Up | Up | Down | Strong trend, LTF dip to enter | Buy the dip at LTF S/R |
| Up | Down | Down | Pullback accelerating | Wait for ITF reversal signal, don't buy yet |
| Down | Down | Up | Strong downtrend, LTF bounce to short | Sell the bounce at LTF S/R |
| Down | Up | Up | Bounce accelerating | Wait for ITF exhaustion, don't short yet |
| Range | Up | Up | Range breakout attempt | Buy if ITF structure breaks above HTF range |
| Range | Down | Down | Range breakdown attempt | Sell if ITF structure breaks below HTF range |
| Range | Up | Down | Bounce within range | Fade at HTF resistance |
| Range | Down | Up | Dip within range | Fade at HTF support |

---

## 8. Confluency Scoring

A simple numerical system to quantify alignment strength:

**Rules**:
- +1 for each timeframe aligned with intended trade direction
- −1 for each timeframe opposing
- 0 if timeframe is neutral/ranging

**Example (long trade)**:
| Timeframe | Direction | Score |
|---|---|---|
| HTF | Up | +1 |
| ITF | Up | +1 |
| LTF | Up | +1 |
| **Total** | **+3** | **High confidence** |

| Score | Confidence | Action |
|---|---|---|
| **+3** | Very high | Full position size. Strong trend across all timeframes. |
| **+2** | High | Position size. One timeframe neutral/mildly conflicting — acceptable. |
| **+1** | Moderate | Reduced size. Only one timeframe confirms direction. |
| **0** | Low | Skip or very small. No clear alignment. |
| **−1 or less** | Very low | Do not take trade. Timeframes are conflicting. |

**Alternative weighting** (if you want to weight HTF more heavily):
- HTF = ×2
- ITF = ×1.5
- LTF = ×1

This gives more influence to higher timeframes and reduces noise.

---

## 9. Common Multi-TF Setups

### 9.1 Trend Continuation

The most classic MTFA setup:

1. **HTF**: Strong trend (ADX > 25, MA slope angled).
2. **ITF**: Pullback within HTF trend. Pullback is shallow (38–62% retracement of the prior HTF swing).
3. **LTF**: Reversal pattern on LTF (bullish engulfing, hammer, double bottom) at a key ITF level (38/50/62 fib or ITF MA).

**Example**: Daily trend up. 4H pullback from $52,000 to $49,500 (38% retracement). 15-minute shows a double bottom at $49,500 with bullish engulfing. Enter long.

### 9.2 Breakout Trading

1. **HTF**: Consolidation/range (e.g., weekly range between $48,000 and $52,000).
2. **ITF**: ITF squeezes into HTF resistance (ITF structure tightening, Band Width narrowing).
3. **LTF**: Strong breakout candle closing above HTF resistance with 2× average volume.

**Entry**: On LTF pullback to retest the broken HTF resistance as support (new support).

**Stop**: Below the breakout candle low.

**Target**: HTF measured move (range height projected above breakout).

### 9.3 Reversal Trading

1. **HTF**: Extended trend. HTF RSI > 75 (overbought in uptrend) or < 25 (oversold in downtrend). ADX very high (> 45).
2. **ITF**: ITF divergence forming — price makes a higher high but RSI/MACD makes a lower high (bearish) or lower low with higher RSI/MACD low (bullish).
3. **LTF**: LTF shows a reversal pattern (evening star, bearish engulfing, shooting star for a top; morning star, bullish engulfing, hammer for a bottom).

**Caution**: Reversal trading against the HTF trend is the hardest setup. Wait for clear LTF break of structure (price breaks the HTF trendline on the LTF).

### 9.4 Pullback Entry (The Most Common Setup)

This is the workhorse of trend trading:

1. **HTF direction confirmed** (trend is up/down).
2. **Wait for ITF pullback** to a key level (ITF 50/100 EMA, ITF fib retracement, ITF previous resistance-turned-support).
3. **Watch LTF for reversal confirmation** at that level.
4. **Enter** on LTF reversal candle close.
5. **Stop** below the ITF pullback low (long) or above the ITF pullback high (short).

**Key**: The ITF level you use for entry must be visible and meaningful. Don't enter on an arbitrary pullback level. Wait for the level to be tested.

### 9.5 Failure Swing / Tap and Reverse

1. **HTF**: Range or trend.
2. **ITF**: Price pushes beyond ITF S/R but immediately reverses.
3. **LTF**: LTF shows a failure pattern — a breakout bar that closes poorly (long upper wick above resistance = failure, long lower wick below support = failure).

**Example**: ITF resistance at $52,000. Price pushes to $52,200 (above resistance) but the 4H candle closes at $51,800 (inside the range). Called a "spring" or "trap." LTF shows a bearish engulfing around the failure. Enter short.

---

## 10. Indicator Alignment Across Timeframes

### 10.1 RSI Across Timeframes

| HTF RSI | ITF RSI | LTF RSI | Interpretation |
|---|---|---|---|
| 60+ (strong) | 40–50 (neutral/pullback) | 30–40 (oversold) | Trend entry opportunity. HTF uptrend, ITF pulling back, LTF getting oversold. |
| 30–40 (weak) | 60–70 (overbought) | 70+ (overbought) | Short entry opportunity. HTF downtrend, ITF bouncing, LTF overbought. |
| 70+ (overbought extended) | 70+ (overbought) | 70+ (overbought) | All timeframes overbought. Trend extremely extended. Reversal possible. Stand aside. |
| 40–60 (neutral) | 40–60 (neutral) | 40–60 (neutral) | No edge. Market directionless. |

### 10.2 MACD Across Timeframes

| Condition | Interpretation |
|---|---|
| All three MACDs bullish (signal line above 0, histogram rising) | Strong momentum, all vectors aligned. |
| HTF MACD bullish, ITF MACD pulling back (histogram falling, signal line still above 0) | Trend dip. Entry opportunity if LTF shows reversal. |
| HTF MACD bearish, ITF MACD bullish | Counter-trend bounce. Short opportunity on exhaustion. |
| All three MACDs bearish | Strong downtrend. Fade rallies, don't try to catch bottom. |

### 10.3 Moving Averages Across Timeframes

| HTF MA | ITF MA | LTF MA | Interpretation |
|---|---|---|---|
| Price above 200 SMA | Price above 50 SMA | Price above 20 EMA | Full alignment bullish. |
| Price above 200 SMA | Price tested 50 SMA (bounced) | Price crossed above 20 EMA | Pullback completion in uptrend. Buy. |
| Price below 200 SMA | Price below 50 SMA | Price below 20 EMA | Full alignment bearish. |
| Price below 200 SMA | Price tested 50 SMA (rejected) | Price crossed below 20 EMA | Bounce exhaustion in downtrend. Short. |

### 10.4 Volume Across Timeframes

| HTF Volume | ITF Volume | LTF Volume | Interpretation |
|---|---|---|---|
| Above average | Above average | Spiking | Trend with broad participation. High conviction. |
| Above average | Declining | Low | Trend losing steam on ITF/LTF. Caution. |
| Below average | Below average | Spiking on reversal | Low HTF commitment but short-term spike. May be a trap. |
| Below average | Low | Low | No conviction anywhere. Stand aside. |

---

## 11. Divergence Across Timeframes

### 11.1 LTF Divergence Within HTF Trend

The most powerful divergence signal: divergence on the LTF that aligns with the HTF direction.

**Example**:
- **HTF trend**: Up
- **ITF pullback**: Price pulling back
- **LTF divergence**: Price makes a lower low on LTF, but LTF RSI makes a higher low

**Meaning**: The pullback is losing momentum on the LTF. Bullish divergence within a larger uptrend. Very high probability entry signal.

**Why it works**: The HTF uptrend means buyers are in control. The LTF divergence means the pullback is weakening. These two factors reinforce each other.

### 11.2 HTF Divergence

HTF divergence (daily or weekly) is the most significant signal in technical analysis. It identifies major trend reversals.

When analyzing HTF divergence across timeframes:
- **Daily divergence** → Valid for weeks to months.
- **Weekly divergence** → Valid for months to a year.
- **4H divergence** → Valid for days to weeks.
- **1H divergence** → Valid for hours to days.

**Multi-timeframe divergence confirmation**:

> If the DAILY chart has bearish divergence AND the 4H chart also has bearish divergence, the signal is extremely strong. If only the daily has divergence but 4H doesn't, the move may need more time to develop.

---

## 12. Timeframe Mismatch and Common Mistakes

| Mistake | Why It Fails | Fix |
|---|---|---|
| Trading LTF signal without HTF check | Counter-trend entries get run over | Start MTFA from HTF, not LTF |
| Using timeframes too close together | No additional information (e.g., 5m + 3m) | Ensure 3–6× ratio between timeframes |
| Equal weighting of all timeframes | HTF should outweigh LTF | Weight HTF 2×, ITF 1.5×, LTF 1× |
| Entering on HTF signal without LTF confirmation | Entry too early, no precision | Wait for LTF confirmation within HTF direction |
| Ignoring HTF when LTF looks good | "This time is different" — it never is | If HTF opposes, skip the trade |
| Not adjusting stops for HTF levels | Stop within normal HTF noise | Place stops beyond HTF S/R, not just LTF |
| Overanalyzing (paralysis) | Too many timeframes cause confusion | Stick to 3 timeframes: HTF, ITF, LTF |
| Confirmation bias | Finding only evidence for your bias | Write down the opposing case first |

---

## 13. MTFA in Crypto Markets

Crypto markets have unique characteristics that affect multi-timeframe analysis:

### 24/7 Trading
- No daily close = continuous cycle. Traditional daily/weekly analysis still works but the "close" is arbitrary (midnight UTC).
- Weekend gaps don't exist. Support/resistance levels don't have weekend gaps to fill.
- Always monitor across weekends — crypto can make major moves on Saturday/Sunday.

### Compressed Cycles
- A crypto "year" (market cycle) is roughly 4 human years.
- This means timeframe compression: a 1-year crypto trend may behave like a 4-year stock trend.
- Daily charts in crypto can show moves that would take weeks in stocks.
- 4H in crypto often carries the weight of daily in traditional markets.

### Multi-Exchange Fragmentation
- Different exchanges may show different structures on the same timeframe due to varying liquidity.
- Binance is generally the reference pair. OKX, Coinbase may differ slightly.
- **For the AI**: When analyzing a chart on LMView, note which exchange the data is from. Binance data is primary and most liquid.

### Algo-Driven Squeezes
- Crypto has high retail participation + aggressive market makers.
- HTF structure can compress for weeks, then explode in days.
- Multi-timeframe alignment changes rapidly during these moves.

**Crypto-specific MTFA tips**:
- Use 4H as your primary trend timeframe (equivalent to daily in stocks).
- Use 1H as your ITF for intraday moves.
- Use 15m as your LTF for entries.
- Always check the daily/weekly for major support/resistance levels, even if you trade 4H/1H.

---

## 14. Practical Analysis Workflow

### Step-by-Step MTFA Process

**Step 1 — Determine HTF Direction**
- Open the highest timeframe you plan to use (daily for swing, 4H for intraday).
- Draw key S/R levels.
- Identify trend direction: make sure you know which way is the "path of least resistance."
- **Decision**: Only trade in the direction of the HTF trend (or at HTF range boundaries if ranging).

**Step 2 — Identify ITF Setup**
- Switch to the middle timeframe.
- Look for pullback, bounce, or consolidation within the HTF direction.
- Mark potential entry levels: HTF S/R, ITF moving average, ITF fib retracement, ITF trendline.
- **Decision**: Identify 1–3 concrete levels where you would consider entry.

**Step 3 — Time Entry on LTF**
- Switch to the lower timeframe.
- Watch for a specific entry trigger at the ITF level: reversal candle pattern, LTF structure break, divergence, or indicator crossover.
- Place stop: below the ITF structure level (long) or above (short).
- Set target: first target ITF S/R, second target HTF S/R.

**Step 4 — Manage the Trade**
- If LTF setup triggers and price moves in your direction, move stop to breakeven after 1× ATR move.
- Trail stop using ITF structure (e.g., below the most recent ITF pullback low).
- Scale out at ITF target, let remainder run to HTF target.

### Quick MTFA Checklist

Before taking any trade:
- [ ] HTF direction identified (up / down / ranging)
- [ ] HTF key S/R levels drawn
- [ ] HTF trend consistent with trade direction
- [ ] ITF setup identified (pullback/bounce/breakout/breakdown)
- [ ] ITF confirms trade direction
- [ ] LTF entry trigger identified
- [ ] Stop placed beyond ITF structure
- [ ] 1st target at ITF S/R, 2nd target at HTF S/R
- [ ] Risk per trade ≤ 1–2% of total capital

### AI Response Template

When a user asks about a chart or setup:

> "Let's analyze this from a multi-timeframe perspective. On the [HTF] chart, the structure is [bullish/bearish/ranging] — we can see [key observation]. On the [ITF], price is in a [pullback/bounce/breakout] from [level]. On the [LTF], we're seeing [entry trigger]. This gives us a confluency score of [X/3] for a [trade direction] trade. The primary risk is [potential regime change on HTF]."

---

## 15. LMView-Specific Timeframe Handling

### Supported Timeframes

LMView supports: `1s`, `1m`, `5m`, `15m`, `1h`, `4h`, `1d`, `1w`

**Recommended MTFA sets by user objective:**

| Objective | HTF | ITF | LTF |
|---|---|---|---|
| Scalping (very short) | 1m | 5m | 1m* |
| Scalping | 15m | 5m | 1m |
| Intraday | 1H | 15m | 5m |
| Swing | 4H | 1H | 15m |
| Position (multi-week) | 1D | 4H | 1H |
| Long-term (multi-month) | 1W | 1D | 4H |

*Scalping LTF is the same as HTF — scalpers often use tape/order flow instead of LTF indicators.

### 1-Second Timeframe Note

The `1s` timeframe is unique. It shows each second as a candle and is **not suitable** for traditional candlestick pattern analysis. It is primarily used for:
- Tape reading with visual candlestick representation
- Executing high-frequency entry timing
- Tick-level structure analysis

For MTFA, 1s should only be used as LTF for the fastest scalping approaches. Traditional MTFA rules (patterns, divergence) are unreliable below 1m.

### Multi-Timeframe Display in LMView

LMView displays multiple timeframes in different ways:
- **Chart timeframe tabs** — Switch between timeframes to check each level.
- **Watchlist** — Show performance across multiple timeframes for symbol screening.
- **Market overview** — Show top movers on 1H, 4H, 1D.

---

## 16. References and Further Reading

### Books
- *Technical Analysis of the Financial Markets* by John J. Murphy — Classic MTFA methodologies.
- *Trading for a Living* by Alexander Elder — Triple-screen trading system (the original structured MTFA).
- *Come into My Trading Room* by Alexander Elder — Practical MTFA for different trading styles.
- *Encyclopedia of Chart Patterns* by Thomas N. Bulkowski — Pattern reliability across timeframes.
- *The Best Trend Following Methods* by Bo Yoder — Multi-timeframe trend identification.

### Trading Platforms and Resources
- **TradingView** — Multiple chart layouts for side-by-side MTFA.
- **Sierra Chart** — Advanced multi-timeframe studies and alerts.
- **Thinkorswim (TD Ameritrade)** — Timeframe segmentation and scanning.

### LMView-Specific
- `Market_Regime_Detection.md` — Use this to identify which regime each timeframe is in.
- `Technical_Analysis.md` — Indicator usage across different timeframes (RSI periods, MA settings).
- `Chart_Pattern_Encyclopedia.md` — Pattern reliability and multi-timeframe pattern alignment.
