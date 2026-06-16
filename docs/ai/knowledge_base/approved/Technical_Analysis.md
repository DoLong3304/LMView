# KNOWLEDGE BASE: TECHNICAL ANALYSIS CRYPTO

> **Metadata**: `review_status: approved` | `allowed_for_rag: true` | `internal_only: false`
> **Version scope**: 0.25.x | **Last reviewed**: 2026-06-16


## Table of Contents
1. Objectives, scope, and safety principles
2. Technical analysis fundamentals in crypto
3. Market data and backend/frontend requirements
4. Price action, candlestick, trend, support/resistance
5. Breakout, fakeout, pullback and volume confirmation
6. Multi-timeframe analysis
7. Core indicators: RSI, MACD, SMA/EMA, Bollinger Bands, VWAP, ATR, Ichimoku, Stochastic RSI, ADX, Fibonacci, Volume Profile
8. Framework for combining signals and risk management
9. Knowledge base for AI Agent: intent, response rules, guardrails, and checklist
10. Operational checklist
11. Glossary
12. Main references
Appendix A, B, C, D

## 1. Objectives, scope, and safety principles
### 1.1. Objectives of the knowledge base
This knowledge base is designed for a crypto dashboard system featuring price data, volumes, indicators, and an AI Agent chatbot. The goal is to help the Agent understand terminology correctly, explain technical signals properly, know when to request more data, how to add/edit/remove tools on the chart, and how to warn about risks when users over-extrapolate signals.
A good AI Agent doesn't just say "RSI is overbought" or "MACD crossed up." It places the signal in context: macro trend, price position relative to support/resistance, volume, volatility, liquidity, timeframe, funding/open interest (if analyzing perpetual futures), and the risk level if leverage is used.

### 1.2. Scope of Application

| Scope | Includes | Excludes |
|---|---|---|
| **Market** | Crypto spot, perpetual futures, major coins, altcoins, BTC dominance/TOTAL (if data available). | Deep tokenomics valuation, deep on-chain forensics (if backend lacks data). |
| **Data** | OHLCV, order book, funding rate, open interest, liquidations, VWAP, volume profile. | Speculating on data not present in the system. |
| **Analysis** | Price action, trend, S/R, volume confirmation, indicator interpretation, multi-timeframe analysis. | Definitive buy/sell commands, guaranteed win rates. |
| **Users** | TA beginners, short-term traders, watchlist managers, dashboard users. | Acting as a licensed financial advisor. |

### 1.3. Safety principles for the AI Agent
* **Always state the timeframe being analyzed.** A coin can be bullish on the 15m chart but bearish on the 1D chart.
* **Never use a single indicator to draw conclusions.** At a minimum, combine price action, trend, price zones, volume, and volatility.
* **Do not use words like "certain", "guaranteed", "all-in", or "cannot drop".** Use probabilistic language: likely, leaning towards, unconfirmed signal.
* **When data is missing, state that it is missing.** For example, if volume is missing, do not confirm a breakout using volume.
* **For perpetual futures, always remind users of funding, liquidation, leverage, and 24/7 volatility risks.**
* **Every signal must come with invalidation conditions:** at what closing price does the thesis become wrong?
* **Do not give personalized financial recommendations** without knowing the user's risk appetite, capital, leverage, holding period, and experience.

### 1.4. Classifying signal reliability levels

| Level | Minimum Conditions | How the Agent should express it |
|---|---|---|
| **Weak** | One indicator fires, but trend/volume/zones do not support it. | "This is an early signal, not yet sufficiently confirmed." |
| **Medium** | 2-3 factors align, but lacks volume or the candle hasn't closed. | "The scenario leans towards X, but needs a candle close/volume confirmation." |
| **Strong** | Macro trend, price zone, volume, indicator, and MTF all align. | "The signal has strong confirmation, but still requires a stop/invalidation level." |
| **Invalid** | Missing data, broken indicator, extreme noise, or severe timeframe conflicts. | "No conclusions should be drawn from the current data." |

## 2. Technical analysis fundamentals in crypto
### 2.1. What is Technical Analysis?
Technical Analysis (TA) is the study of market behavior through price, volume, and related market data to identify trends, supply/demand zones, momentum, volatility, and probabilistic scenarios.
In crypto, TA is highly popular due to 24/7 trading, real-time data, massive retail participation, strong herd mentality, and the lack of traditional cash-flow fundamentals for many assets. However, crypto TA is also prone to "noise" due to fragmented liquidity, high volatility, immense leverage, and liquidity sweeps.

### 2.2. Four information layers of a crypto chart

| Information Layer | Examples | Analytical Meaning |
|---|---|---|
| **Price** | OHLC, swing high/low, close, wick. Gaps are rare due to 24/7 trading. | Shows trend structure, price rejection zones, breakouts/fakeouts. |
| **Volume** | Spot vol, futures vol, relative vol, volume delta. | Confirms participation, supply/demand absorption, breakout reliability. |
| **Volatility** | ATR, Bollinger BandWidth, range expansion/compression. | Estimates stops, targets, squeeze/breakout environments, prevents over-leveraging. |
| **Derivatives context** | Funding rate, open interest, liquidation heatmaps, basis. | Identifies crowding, squeezes, liquidation cascades in perps. |

### 2.3. Differences between crypto TA and traditional markets

| Factor | Crypto | Traditional Stocks/Commodities | Implications for the Agent |
|---|---|---|---|
| **Trading hours** | 24/7, no standard market open/close. | Defined trading sessions, weekends, opening gaps. | Session-based indicators like VWAP require clearly defined anchors. |
| **Exchanges** | Multiple exchanges; fragmented price and volume. | Usually a primary listed exchange with standardized data. | Must state the data source (Binance, Coinbase, aggregate...). |
| **Leverage** | Perpetual futures dominate; funding and liquidations heavily impact price. | Futures/options exist but are less common for everyday retail. | Do not analyze futures using only spot charts if derivative data is available. |
| **News/Events** | Listings, unlocks, hacks, regulations, on-chain whale movements. | Earnings, macro data, rate decisions, commodity inventory. | Check news/on-chain tools when abnormal price movements occur. |
| **Liquidity** | Altcoins can be thin, wide spreads, easy to pump/dump. | Large-caps are deeper with stable market makers. | Volume confirmation must be weighed against actual liquidity and spread. |

### 2.4. Market structure: trend, range, transition
Every analysis should start by asking: Is the market trending, ranging, or transitioning?
Indicators only make sense in the right market regime. MACD/MA work in trends; RSI/StochRSI work in ranges; ATR measures risk regardless of direction.

| Market Regime | Signs | Suitable Tools | Common Mistakes |
|---|---|---|---|
| **Uptrend** | Higher High, Higher Low. Price above main EMAs. Pullbacks hold support. | EMA/SMA, trendlines, MACD, ADX, Fibonacci retracement, volume pullback. | Selling just because RSI > 70 in a strong trend. |
| **Downtrend** | Lower High, Lower Low. Price below main EMAs. Bounces get sold. | EMA/SMA, MACD, ADX, ATR stops, Fibonacci retracement from swing highs. | Catching knives just because RSI < 30 in a strong downtrend. |
| **Range** | Price oscillates between support/resistance. Low ADX, flat MAs. | RSI, StochRSI, Bollinger, VWAP, support/resistance. | Buying fake breakouts in thin liquidity zones. |
| **Transition** | Break of structure, retest, volume spikes, indicators shift phase. | S/R role reversal, volume confirmation, MTF, ATR expansion. | Entering too early before the candle closes and before the retest. |

## 3. Market data and backend/frontend requirements
### 3.1. OHLCV Candles
Candles are the base unit of TA (1m, 5m, 15m, 1H, 4H, 1D, 1W). Because crypto is 24/7, candles need a clear timezone (usually UTC).
* **open_time / close_time:** Start and end time. Must not overlap.
* **open:** Starting price.
* **high:** Highest price.
* **low:** Lowest price.
* **close:** Ending price. Used for most indicators.
* **volume:** Traded volume. Must specify base or quote volume.

### 3.2. Crypto-specific data issues
* Volume varies by exchange. A Binance breakout may not look the same on Coinbase.
* Aggregate volume must be explicitly labeled.
* Wash trading can distort low-cap signals. Alert if volume spikes but order book depth does not support it.
* Perp futures have OI and funding. Price up + OI up = new money. Price up + OI down = short covering.
* New altcoin listings lack history, making EMA200 or long-term RSI unstable.

### 3.3. Minimum Schema for Indicator Engine
* **OHLCV:** timestamp, open, high, low, close, volume_base, volume_quote.
* **Exchange metadata:** exchange, symbol, market_type, quote_asset, contract_type.
* **Derivatives:** funding_rate, open_interest, long_short_ratio, liquidation_volume.
* **Order book:** bid/ask spread, depth, imbalance.
* **Computed indicators:** indicator_name, params, timeframe, value, status.

### 3.4. Pre-analysis Data Quality Check Rules for the Agent
* Check for missing candles. Missing data breaks MAs/RSI/MACD.
* Check for price outliers (wicks from exchange glitches vs real liquidations).
* Check for zero volume. If missing, do not say "volume confirms".
* Check if there are enough candles for the period (e.g., EMA200 needs 200+ candles).
* Ensure the timeframe matches the user's question ("today" vs "long-term trend").

## 4. Price action, candlestick, trend, and support/resistance
### 4.1. What is Price Action?
Price action is reading market behavior directly from candle structures, swing highs/lows, support/resistance zones, impulses, corrections, wicks, and reactions at key levels. In crypto, price action is prioritized because the market reacts instantly to news, leverage, and liquidity.

| Concept | Identification | Meaning |
|---|---|---|
| **Swing high** | Local peak higher than neighboring candles. | Take-profit zone, resistance, trendline anchor. |
| **Swing low** | Local trough lower than neighboring candles. | Support zone, invalidation level, trendline anchor. |
| **Impulse leg** | Rapid price move, large bodies, little overlap. | Aggressive capital flow, often creates key price zones. |
| **Corrective leg** | Slow pullback, small candles, declining volume. | Healthy pullback if structure holds. |
| **Liquidity sweep** | Price sweeps past an old high/low then closes back inside. | Fakeout, stop hunt, or liquidity absorption. |

### 4.2. Candlesticks
Candlesticks show the open, high, low, and close. The body shows the distance between open and close; the wick shows rejected prices. Always read candles in context (location, trend, volume, timeframe).

| Candle Element | Interpretation | Warning |
|---|---|---|
| **Long body** | Strong buying/selling pressure. | A long body right at S/R could be exhaustion if volume is abnormal. |
| **Long upper wick** | Price rejected at the highs. | Not an automatic reversal; needs confirmation from the next candle. |
| **Long lower wick** | Price rejected at the lows. | In a strong downtrend, this might just be short-term short-covering. |
| **Doji / Spinning top** | Indecision, supply/demand balance. | Does not signal reversal unless at a key structural zone. |
| **Engulfing** | Latter candle completely engulfs the former. | Stronger if located at S/R with rising volume. |

### 4.4. Trend
Uptrend: Higher Highs (HH) + Higher Lows (HL).
Downtrend: Lower Lows (LL) + Lower Highs (LH).
Range: Swing highs/lows do not expand clearly; price oscillates horizontally.

### 4.5. Support and Resistance (S/R)
Support: Price zone where demand stops price from falling.
Resistance: Price zone where supply stops price from rising.
*Treat S/R as zones, not absolute lines, especially in crypto due to heavy wicks.*

### 4.6. Role Reversal
When support breaks cleanly, it becomes resistance. When resistance breaks cleanly, it becomes support. In crypto, role reversals are reliable only with clear candle closes, successful retests, and supporting volume/volatility.

## 5. Breakout, fakeout, pullback and volume confirmation
### 5.1. Breakout
Price breaks out of resistance, support, a range, trendline, or pattern. Breakouts are reliable when the candle closes outside the zone, volume/volatility expands, and the retest holds. Crypto breakouts are frequently fake due to stop hunts.

| Confirmation Factor | How to Evaluate | Weak Signal |
|---|---|---|
| **Close confirmation** | Candle closes outside the S/R zone. | Only wicks past the zone and closes back inside. |
| **Volume confirmation** | Volume higher than average, rising RVOL. | Breakout with low volume or volume isolated to a small exchange. |
| **Retest** | Price returns to the breakout zone and it holds as new support/resistance. | Price immediately loses the zone on the retest. |

### 5.2. Fakeout
A false breakout. Price crosses a key level but fails to sustain it, reversing back into the previous range. Often occurs around liquidity zones (old highs/lows, round numbers) or when funding/OI is heavily skewed.
*Agent response style:* "This is not a confirmed breakout; it leans towards a liquidity sweep/fakeout because the wick is long and the close returned to the range."

### 5.3. Pullback
A temporary retracement against the main trend. A healthy pullback has moderate amplitude, declining volume, and holds dynamic S/R. A dangerous pullback breaks key swing lows/highs with rising counter-trend volume.

### 5.4. Volume confirmation
Checking if capital flow supports the price movement (VSA/Wyckoff principles). Look at volume bars, candle spreads, and closing positions.
* **Relative Volume (RVOL)** = Current Vol / Average Vol(n). Breakouts are stronger when RVOL > 1.5 or 2.0 with a favorable close.

## 6. Multi-timeframe analysis (MTF)
MTF avoids mistaking short-term noise for long-term trends. A 15m long signal has low probability if price is hitting a 1W resistance.
* **Top-down 5 steps:** 1. Macro timeframe (identify regime). 2. Macro timeframe (mark S/R). 3. Intermediate timeframe (check structure, EMAs). 4. Entry timeframe (wait for trigger like engulfing, RSI div). 5. Risk (set invalidation, stops, targets).

## 7. Core technical indicators
Indicators do not predict the future; they transform past price/volume data into readable formats. The Agent must explain what the indicator measures, the parameters used, the current signal, confirmation conditions, and fake signal risks.

* **RSI (Relative Strength Index):** Measures momentum (0-100). Default 14. >70 overbought, <30 oversold. Warning: can stay overbought for long periods during strong trends.
* **MACD:** Measures trend and momentum (EMA 12, 26, 9). Crossovers and histograms. Warning: lags and produces false signals in tight ranges.
* **SMA/EMA:** Moving averages smooth price data. EMA is more sensitive. EMA 20/50 for short/mid-term, SMA/EMA 200 for macro trend.
* **Bollinger Bands:** SMA 20 + 2 standard deviations. Measures volatility and squeeze. Price riding the band in a strong trend is normal.
* **VWAP / Anchored VWAP:** Volume-weighted average price. Crucial benchmark. Because crypto is 24/7, must define the anchor (daily UTC, weekly, or from a major swing/event).
* **ATR (Average True Range):** Measures volatility, not direction. Excellent for setting stop-losses (e.g., Entry +/- 2 * ATR) to avoid getting wicked out in crypto.
* **Ichimoku:** Comprehensive system for trend, S/R, and momentum. Cloud (Kumo) indicates macro support/resistance.
* **Stochastic RSI:** Highly sensitive oscillator. Useful for pullbacks in a trend, but very noisy on low timeframes.
* **ADX:** Measures trend strength (not direction). ADX < 20 means weak trend/range. ADX > 25 means strong trend.
* **Fibonacci:** 23.6%, 38.2%, 50%, 61.8%, 78.6%. Used for retracement levels and extensions. Stronger when confluent with other S/R or volume nodes.
* **Volume Profile:** Distributes volume across price levels instead of time. Identifies Point of Control (POC), High Volume Nodes (HVN), and Low Volume Nodes (LVN). Requires backend tick/trade data to be accurate.

## 8. Framework for combining signals and risk management
### 8.1. Confluence
Confluence is the alignment of multiple independent factors. A setup is stronger if it has S/R, Fibonacci, VWAP, Volume Profile, RSI divergence, and a confirmation candle. (Avoid redundant indicators like using RSI, StochRSI, and MACD simultaneously, as they all measure momentum).

### 8.4. Stop loss and position sizing
TA is meaningless without risk management. Crypto's 24/7 nature, wicks, and liquidation cascades make stops critical.
* Risk per trade = Account Equity * Risk %
* Position Size = Risk per trade / Distance to Stop
* The Agent should help users understand the "invalidation point" rather than just providing a target.

### 8.5. Common Mistakes
* Using RSI overbought/oversold against a strong trend.
* Entering breakouts before the candle closes.
* Drawing too many S/R lines, cluttering the chart.
* Failing to distinguish spot charts from perp futures charts.
* Ignoring funding fees, slippage, and liquidation risks when using leverage.

## 9. Knowledge base for AI Agent chatbot
### 9.2. Chart analysis response rules
* Start with context: symbol, market type, timeframe, data source.
* Summarize regime: uptrend/downtrend/range.
* List key price zones: S/R, invalidation.
* Read volume and indicators.
* Provide 2-3 scenarios instead of one absolute conclusion. Every scenario needs activation and invalidation conditions.
* End with a risk warning if leverage/trading is mentioned.

### 9.3. Agent Response Template
"Currently, [Symbol] on the [timeframe] is in an [uptrend/downtrend/range]. The closest support is [S1] and resistance is [R1]. The [indicator] shows [momentum/trend], but this needs confirmation via [volume/close]. The bullish scenario is valid if [condition]; the bearish scenario triggers if [condition]. This thesis is invalidated if price crosses [invalidation]. Note: This is not financial advice."

### 9.5. Handling Missing Data
* No volume -> State volume confirmation is impossible.
* No timeframe -> Ask the user or use the current chart timeframe and state it clearly.
* Insufficient candles -> Warn that long-term indicators (like EMA200) are unstable.

## 11. Glossary
* **Price action:** Reading market behavior directly via candles, swings, S/R, and reactions.
* **Candlestick:** Open, high, low, close for a specific period.
* **Breakout:** Price breaking out of an S/R zone.
* **Fakeout:** False breakout; price crosses a level but reverses back.
* **Pullback:** Temporary retracement against the main trend.
* **Volume Profile:** Volume distributed by price levels (POC, HVN, LVN).
* **Funding rate:** Periodic payment between longs/shorts in perp futures.
* **Open interest:** Total outstanding derivative positions.
* **Liquidation:** Forced closure due to insufficient margin.

## 12. Main References
* John J. Murphy - Technical Analysis of the Financial Markets
* VSA/Wyckoff Methodology resources
* Carolyn Boroden - Fibonacci Trading
* Wayne Gorman & Jeffrey Kennedy - Visual Guide to Elliott Wave Trading
* StockCharts ChartSchool
* CME Group Education
* Binance Academy / Investopedia

*(Appendix A, B, C, D details implementation specs, specific playbooks for breakouts/pullbacks, dialogue examples, and crypto-specific TA involving funding/OI/liquidations, seamlessly integrating derivative metrics into classical charting).*