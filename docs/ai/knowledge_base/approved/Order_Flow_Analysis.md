# Order Flow Analysis — Complete Guide

> **Document Type**: Educational Reference
> **Audience**: AI Assistant, End Users
> **Version**: 0.27.0+
> **Domain**: Market Microstructure, Technical Analysis

---

## Table of Contents

1. What Is Order Flow?
2. Core Concepts: Aggressive vs Passive Orders
3. The Order Book — Battleground of Supply and Demand
4. Cumulative Volume Delta (CVD) — The Primary Order Flow Tool
   - 4.1 Calculation
   - 4.2 Interpretation
   - 4.3 CVD Divergence
   - 4.4 CVD vs Price Confirmation
5. Footprint Charts — Per-Price-Level Volume
   - 5.1 Delta at Each Price
   - 5.2 Point of Control (POC)
   - 5.3 Value Area (VA) and Value Area High/Low (VAH/VAL)
   - 5.4 Volume Profile Structure
6. Absorption and Exhaustion Patterns
   - 6.1 Buying Climax
   - 6.2 Selling Climax
   - 6.3 Absorption at Key Levels
   - 6.4 Stopping Volume / Reversal Patterns
7. Delta Divergence — The Most Reliable Order Flow Signal
   - 7.1 Bullish Divergence
   - 7.2 Bearish Divergence
   - 7.3 Hidden Divergence (Trend Continuation)
   - 7.4 Timeframe Considerations
8. Iceberg Orders and Hidden Liquidity
9. Open Interest and Liquidations
10. Volume Profile Concepts
    - 10.1 High-Volume Nodes (HVNs) and Low-Volume Nodes (LVNs)
    - 10.2 POC Migration
    - 10.3 Single Prints and Gaps
11. Order Flow Imbalance Metrics
    - 11.1 Bid-Ask Volume Imbalance
    - 11.2 Delta Accumulation
12. Intraday vs Swing Order Flow
13. Practical Analysis Playbook
14. Known Limitations and Warning
15. References and Further Reading

---

## 1. What Is Order Flow?

Order flow is the **real-time stream of executed trades** showing who is buying aggressively (market buys) and who is selling aggressively (market sells). Unlike the order book, which shows resting limit orders (intentions), order flow shows **actual transactions** — the trades that have already happened.

Order flow analysis answers three questions:
- **Who is in control?** — Buyers or sellers at current prices?
- **Is the move real?** — Is price backed by volume and aggressive participation?
- **Is the move ending?** — Are we seeing absorption, exhaustion, or divergence?

**Key distinction**: Order flow is NOT the same as the order book. The order book is the *before* (resting limit orders that may or may not be there when price reaches them). Order flow is the *after* (what actually executed). Always prioritize executed volume over resting orders.

---

## 2. Core Concepts: Aggressive vs Passive Orders

Every trade has two participants:

| Order Type | Side | Role | Behavior |
|---|---|---|---|
| **Market buy** | Aggressive buyer | Taker | Buys at ask price, consumes liquidity |
| **Market sell** | Aggressive seller | Taker | Sells at bid price, consumes liquidity |
| **Limit buy** (at bid) | Passive buyer | Maker | Waits to be matched; provides liquidity |
| **Limit sell** (at ask) | Passive seller | Maker | Waits to be matched; provides liquidity |

- **Aggressive buying** (market buy / aggressive limit buy) = conviction. Someone is willing to pay the spread for immediate execution.
- **Aggressive selling** (market sell / aggressive limit sell) = conviction. Someone is willing to hit the bid for immediate execution.
- **Delta** = (Aggressive buy volume) − (Aggressive sell volume). Positive delta means net aggressive buying. Negative delta means net aggressive selling.

**Rule of thumb**: When the market is trending, the dominant aggressive side will be aligned with the trend direction. When the market is topping or bottoming, the dominant aggressive side will shift before price reverses.

---

## 3. The Order Book — Battleground of Supply and Demand

Order flow and the order book are two sides of the same coin. The order book shows where liquidity rests; order flow shows how that liquidity gets consumed.

### Key Relationships

- **Bid size shrinking without price decline** → Aggressive sellers consuming bids, but new bids replace them → buying interest absorbing selling pressure → often bullish.
- **Ask size shrinking without price rise** → Aggressive buyers lifting asks, but new asks appear → selling interest absorbing buying pressure → often bearish.
- **Bid wall (large limit buy cluster)** → Usually supportive. But if aggressive sellers eat through it, that's a bearish signal.
- **Ask wall (large limit sell cluster)** → Usually resistance. But if aggressive buyers lift through it, that's a bullish signal.

### Imbalance Calculation

```
Bid-Ask Imbalance = (Total Bid Volume - Total Ask Volume) / (Total Bid Volume + Total Ask Volume)
```

Range: −1 to +1. +0.5 means bid volume is 3× ask volume. Values > +0.3 or < −0.3 are notable, but remember: this is resting liquidity, NOT executed volume. Imbalance can disappear in seconds if orders are canceled (spoofing).

---

## 4. Cumulative Volume Delta (CVD)

### 4.1 Calculation

CVD = sum of (Aggressive Buy Volume − Aggressive Sell Volume) over a defined period.

For each trade bar (tick, second, minute, or custom aggregation):

```
Bar Delta = Buy Volume − Sell Volume
CVD = Cumulative Sum of Bar Deltas
```

Each exchange reports delta data differently:
- **Binance**: Reports `takerBuyQuoteAssetVolume` in 24hr ticker — not per-trade, but useful aggregate.
- **General**: Most per-trade data streams report trade side via `isBuyerMaker` flag (true = aggressive sell, false = aggressive buy).

### 4.2 Interpretation

| CVD Condition | Market Interpretation |
|---|---|
| **CVD rising, price rising** | Healthy uptrend. Buyers in control. Trend likely to continue. |
| **CVD rising, price flat** | Hidden accumulation. Smart money buying into weakness. Typically bullish. |
| **CVD falling, price falling** | Healthy downtrend. Sellers in control. Trend likely to continue. |
| **CVD falling, price flat** | Hidden distribution. Smart money selling into strength. Typically bearish. |
| **CVD flat** | Neutral. No aggressive edge. Market may be waiting for catalyst. |

### 4.3 CVD Divergence

**CVD divergence** is the most reliable order flow signal. It occurs when price and CVD move in opposite directions, indicating the current price move lacks conviction.

#### Bullish CVD Divergence

| Condition | Price is making | CVD is making | Meaning |
|---|---|---|---|
| **Regular bullish** | Lower low | Higher low | Selling exhaustion. Downside momentum weakening. Reversal likely. |
| **Hidden bullish** | Higher low | Higher low | Trend continuation. Pullback lacks selling pressure. Trend resumes. |

#### Bearish CVD Divergence

| Condition | Price is making | CVD is making | Meaning |
|---|---|---|---|
| **Regular bearish** | Higher high | Lower high | Buying exhaustion. Upside momentum weakening. Reversal likely. |
| **Hidden bearish** | Lower high | Lower high | Trend continuation. Rally lacks buying pressure. Trend resumes down. |

### 4.4 CVD vs Price Confirmation

The most powerful signal is CVD and price confirming each other:

- **Trend confirmation**: Price breaks resistance AND CVD breaks to a new high at the same time → Breakout is real, follow-through likely.
- **Trend failure**: Price breaks resistance but CVD stays flat or declines → Breakout is weak, likely to be rejected.
- **Reversal confirmation**: Price tests support but CVD shows higher lows → Selling pressure is drying up, bounce likely.

---

## 5. Footprint Charts — Per-Price-Level Volume

Footprint charts display buy and sell volume at every individual price level within a candle. They reveal internal market structure that candlestick bodies hide.

### 5.1 Delta at Each Price

Each row of a footprint shows:
- **Bid volume** (volume executed at the bid — aggressive sells)
- **Ask volume** (volume executed at the ask — aggressive buys)
- **Delta** per price = Ask − Bid at that level

**How to read a footprint row**:

```
Price     Bid Vol     Ask Vol     Delta
52100     142         389         +247    ← aggressive buying heavy at this level
52080     267         198         -69     ← mild selling pressure
52060     445         112         -333    ← heavy selling pressure
52040     98          76          -22     ← balanced
```

**Key observations**:
- **High delta positive at lows of candle** → Buyers stepping in at lows → support.
- **High delta negative at highs of candle** → Sellers appearing at highs → resistance.
- **POC (Point of Control)** → Price level with highest total volume (bid + ask).
- **POC at candle bottom + bullish delta** → Support established.
- **POC at candle top + bearish delta** → Resistance established.

### 5.2 Point of Control (POC)

The POC is the price level with the highest total traded volume over the analysis period. It represents the **fairest price** — where the most value was exchanged.

- **POC in uptrend shifts higher** → Value is moving up, trend healthy.
- **POC in downtrend shifts lower** → Value is moving down, trend healthy.
- **Price returns to POC** → Often acts as support/resistance. High-traffic area attracts price.
- **Multiple tests of POC without rejection** → POC may be breaking, trend changing.

### 5.3 Value Area (VA)

The Value Area is the price range containing 70% of total volume, centered around the POC. It has two boundaries:

- **Value Area High (VAH)** = Upper boundary of 70% volume range
- **Value Area Low (VAL)** = Lower boundary of 70% volume range

**Interpretation**:
- **Price above VA** → Premium price. May attract selling (or be strongly trending if volume supports).
- **Price below VA** → Discount price. May attract buying (or be in freefall if volume supports).
- **VA expansion** → Trend accelerating. Value is being re-priced rapidly.
- **VA contraction** → Consolidation. Market deciding next direction.
- **Price rejects VA extension** → Fakeout. Order flow did not support the move.

### 5.4 Volume Profile Structure

Volume Profile plots total volume at each price level horizontally, revealing **High Volume Nodes (HVNs)** and **Low Volume Nodes (LVNs)**.

- **HVN** → Price level where lots of trading occurred. Usually acts as support/resistance.
- **LVN** → Price level with little trading. Price may blow through these gaps.
- **POC** → Single highest volume node.

The full Volume Profile is computed from the total volume at each price across all trades in the analysis window, whereas footprint shows per-candle detail.

---

## 6. Absorption and Exhaustion Patterns

### 6.1 Buying Climax

A buying climax occurs when aggressive buying reaches an extreme, price spikes, but then the buying pressure cannot be sustained.

**Footprint characteristics**:
- Massive ask volume (buyers aggressively lifting offers)
- Disproportionately large delta positive
- Large POC at or near the high of the move
- On subsequent candles, delta drops sharply
- Price stops rising despite earlier aggressive buying

**Interpretation**: All buying that wanted to happen has happened. No new buyers remain. Price is likely to reverse or correct.

**Example**: BTCUSD rallies from 50,000 to 55,000 in three candles. The third candle shows 3× normal ask volume at 55,000 POC. Next candle: low volume, no delta, price stalls. This is a buying climax — expect a pullback.

### 6.2 Selling Climax

The mirror image of buying climax. Aggressive selling peaks, delta is extremely negative, price crashes, then sellers disappear.

**Footprint characteristics**:
- Massive bid volume (sellers aggressively hitting bids)
- Extremely negative delta
- Large POC at or near the low
- Subsequent candle shows delta turning positive or flat
- Price stabilizes or bounces

**Interpretation**: The last sellers have sold. No new sellers appear. Bounce or reversal likely.

### 6.3 Absorption at Key Levels

Absorption occurs when a large order or cluster of orders is being absorbed by opposite-side flow without the price moving through the level.

**Characteristics**:
- Price approaches a key level (support/resistance)
- Delta spikes in OPPOSITE direction to what you'd expect
- Example: Price approaches resistance, but CVD rises (buyers absorbing the sell pressure)
- Level holds, price reverses away from it

**Interpretation**: Larger players are absorbing the natural flow at key levels. This often precedes a breakout or reversal, depending on which side is absorbing.

**How to analyze**:
1. Identify a key S/R level.
2. Watch delta and CVD as price approaches.
3. If price approaches resistance but CVD stays positive → absorption of sell orders → breakout likely.
4. If price approaches support but CVD stays negative → absorption of buy orders → breakdown likely.

### 6.4 Stopping Volume / Reversal Patterns

Stopping volume is the signature of a potential major reversal:

1. **High volume down candle** with massive negative delta — panic selling.
2. **Next candle** — price goes lower briefly but delta turns positive — sellers are being absorbed.
3. **Following candle** — price up, delta positive, POC shifts higher — reversal confirmed.

This sequence (sell climax → absorption → reversal up) is the foundation of order-flow-based reversal trading.

---

## 7. Delta Divergence — The Most Reliable Order Flow Signal

### 7.1 Bullish Divergence

```
Price: Lower Low
  CVD: Higher Low
```

Meaning: Despite new lows, the selling pressure (net aggressive selling) is declining. Fewer participants are selling at each successive low. Sellers are exhausted. Bullish.

**Confirmation steps**:
1. Price drops below previous low.
2. CVD does NOT drop below its previous low. Ideally, CVD makes a higher low.
3. After the divergence, look for a bullish reversal candle with positive delta.
4. Entry on confirmation candle close above the prior swing high.

### 7.2 Bearish Divergence

```
Price: Higher High
  CVD: Lower High
```

Meaning: Despite new highs, the buying pressure (net aggressive buying) is declining. Fewer participants are buying at each successive high. Buyers are exhausted. Bearish.

**Confirmation steps**:
1. Price rallies above previous high.
2. CVD does NOT rally above its previous high. Ideally, CVD makes a lower high.
3. After the divergence, look for a bearish reversal candle with negative delta.
4. Entry on confirmation candle close below the prior swing low.

### 7.3 Hidden Divergence (Trend Continuation)

Hidden divergences occur during pullbacks within a trend. They signal that the trend is likely to resume.

**Hidden Bullish** (in uptrend pullback):
```
Price: Higher Low
  CVD: Higher Low
```
Price pullback is shallow, and CVD stays strong — no selling pressure. Trend will resume.

**Hidden Bearish** (in downtrend pullback):
```
Price: Lower High
  CVD: Lower High
```
Price bounce is weak, and CVD stays weak — no buying pressure. Downtrend will resume.

### 7.4 Timeframe Considerations

| Timeframe | Signal Quality | Best Use |
|---|---|---|
| 1m–5m | Low-Moderate | Scalping; many false signals, need tight confirmation |
| 15m–1H | Moderate | Intraday swings; reasonable reliability |
| 4H–1D | High | Swing/position trades; most reliable |
| Weekly | Very High | Major trend reversals; few opportunities |

**Principle**: Higher timeframe CVD divergence is exponentially more reliable. A 4H bearish divergence has more weight than ten 5-minute divergences.

---

## 8. Iceberg Orders and Hidden Liquidity

An **iceberg order** is a large limit order broken into smaller visible slices. The exchange shows only the "tip" of the order; the rest is hidden.

**How to detect icebregs through order flow**:
- Same visible size reappears immediately after being filled. Example: 10 BTC bid at 50,000 gets eaten, then reappears at the same price with 10 BTC. This repeats 5+ times. That's an iceberg — 50 BTC hidden behind a 10 BTC tip.
- Delta shows persistent one-sided flow without price breaking through. Buyers keep lifting asking, but new asks keep appearing at the same level.
- Price grinds sideways at a level with high volume but no breakout. This is often an absorption battle between two large icebergs.

**How to trade icebregs**:
- If an iceberg bid keeps reloading → strong support. Buying that level is safe if you can enter near it.
- If an iceberg ask keeps reloading → strong resistance. Selling that level is safe.
- If price breaks through an obvious iceberg level → the iceberg was likely canceled or absorbed → the break is significant.

---

## 9. Open Interest and Liquidations

For perpetual futures markets (which dominate crypto volume), Open Interest (OI) and liquidations add another layer to order flow analysis.

**Open Interest (OI)** — total number of outstanding perpetual contracts:
- **OI rising + price rising** → New money entering long positions. Trend healthy.
- **OI rising + price falling** → New money entering short positions. Trend healthy (bearish).
- **OI falling + price falling** → Longs capitulating. May be near a bottom.
- **OI falling + price rising** → Shorts covering. May be near a top (short squeeze).
- **OI flat** → No new conviction. Market waiting for catalyst.

**Liquidation cascades**:
- Long liquidation cascade: Price drops → longs liquidated → market order sells → more price drop → more liquidations.
- Short squeeze cascades: Price rises → shorts liquidated → market order buys → more price rise → more squeezes.

**How to read with order flow**:
- High CVD in one direction + OI rising in that direction → Trend genuine.
- High CVD in one direction + OI falling → Mostly liquidation-driven. Reversal likely soon.
- Price spike + massive CVD + OI drop → Likely a squeeze/climax → caution.

**Key exchanges for OI data**: Binance Futures, Bybit, OKX, Deribit. Note: OI data is exchange-specific and may differ significantly between venues.

---

## 10. Volume Profile Concepts

### 10.1 High-Volume Nodes (HVNs) and Low-Volume Nodes (LVNs)

| Node Type | Definition | Market Behavior |
|---|---|---|
| **HVN** (High Volume Node) | Price level with high traded volume | Attracts price back (like a magnet); acts as support/resistance |
| **LVN** (Gap/Thin zone) | Price level with low traded volume | Price often moves quickly through it; no commitment at those prices |
| **POC** (Point of Control) | Highest single-volume level | Strongest magnet; the "fair price" |

**Trading use**:
- When price is above POC, look for HVN below as support levels for pullbacks.
- When price is below POC, look for HVN above as resistance for bounces.
- Price breaking out of VA range through an LVN → momentum move likely to continue.
- Price rejecting at an HVN → reversal likely.

### 10.2 POC Migration

The POC shifts over time as new volume accumulates:
- **POC rising over multiple sessions** → The market is finding value at higher prices. Uptrend intact.
- **POC falling over multiple sessions** → The market is finding value at lower prices. Downtrend intact.
- **Current price far from POC** → Extended move. Price may revert toward POC (regression).
- **POC stays flat while price trends away** → Trend may be weak (low conviction).

### 10.3 Single Prints and Gaps

A **single print** is a price level with volume at only one time period. It indicates a rapid move through an area with no subsequent trading.

- **Single print above current price** → Unfilled gap, may act as resistance.
- **Single print below current price** → Unfilled gap, may act as support.
- **Multiple single prints stacking** → Momentum move with no value area established.

---

## 11. Order Flow Imbalance Metrics

### 11.1 Bid-Ask Volume Imbalance

At any price level within a candle or time window:

```
Imbalance Ratio = (Ask Volume − Bid Volume) / (Ask Volume + Bid Volume)
```

- Range: −1 to +1.
- **+0.5 or higher** → Strong aggressive buying at that level.
- **−0.5 or lower** → Strong aggressive selling at that level.
- **Near 0** → Balanced, no edge.

**Context matters**: A +0.8 imbalance at resistance means buyers are aggressively trying to break through. A +0.8 imbalance at support after a downtrend means strong buying interest — support is likely to hold.

### 11.2 Delta Accumulation

Track cumulative delta over specific windows:

- **Pre-session delta**: Net aggressive volume before a major event (news, open, settlement). Shows positioning.
- **Session delta**: Current session's net aggressive volume. Shows who's in control.
- **Accumulation delta**: On large timeframes, tracking CVD over days/weeks reveals smart money positioning that the naked chart hides.

---

## 12. Intraday vs Swing Order Flow

| Aspect | Intraday (1m–15m) | Swing (4H–Daily) |
|---|---|---|
| **Primary tools** | Footprint delta, tape reading, level 2 | CVD divergence, Volume Profile, POC analysis |
| **Signal reliability** | Lower — more noise | Higher — fewer but stronger signals |
| **Iceberg detection** | Critical — icebregs control intraday moves | Less relevant — large players work over days |
| **Liquidation cascades** | Frequent — watch OI changes | Rare — mostly institutional flow |
| **Best patterns** | Absorption, stopping volume, delta rejection | CVD divergence, POC migration, HVN rejection |
| **Risk management** | Tight stops (0.5–1× ATR) | Wider stops (2–3× ATR) |

---

## 13. Practical Analysis Playbook

Use this step-by-step approach for any order flow analysis:

### Step 1: Identify the Context
- What is the HTF trend? (Daily/4H)
- Where is price relative to key S/R levels?
- Is there a major news event coming? (FOMC, CPI, earnings, etc.)

### Step 2: Read the Order Book
- Check spread width (normal or expanded?)
- Look for large walls within ±0.5% of current price
- Note imbalance — but remember it's resting, not executed

### Step 3: Check CVD Direction
- Is CVD rising or falling?
- Is CVD confirming or diverging from price?
- Check CVD over multiple timeframes (1m, 5m, 1H)

### Step 4: Analyze Footprint (if available)
- Current candle: where is volume? Which side is aggressive?
- POC location (top, center, bottom of range?)
- Any single prints or volume gaps?

### Step 5: Check Absorption
- Is price stuck at a level with high volume?
- Is one side aggressively absorbing the other?
- Which side keeps reloading (iceberg behavior)?

### Step 6: Check OI and Liquidations (perp markets)
- Is OI rising or falling with price?
- Are liquidation clusters near current price?

### Step 7: Conclude
- **Trend healthy** → CVD + OI + price aligned → Favor trend.
- **Trend weakening** → CVD diverging, absorption at level → Prepare for reversal.
- **Trend exhausted** → Climax volume + massive delta + OI drop → Reversal or deep pullback likely.
- **No edge** → Flat CVD, no imbalance, no absorption → No trade.

### Step 8: Risk-Aware Response
- State confidence (low/medium/high) based on convergence of signals.
- Always note: "Order flow is not predictive — it measures current participation, which can change instantly."
- For users asking about specific trades, remind them that order flow analysis complements but does not replace proper risk management.

---

## 14. Known Limitations and Warning

### What Order Flow CAN Tell You
- Where aggressive participation is happening.
- Whether a move is backed by real conviction.
- Whether buying or selling pressure is exhausting.
- Where hidden liquidity (icebregs) may be positioned.

### What Order Flow CANNOT Tell You
- **Future price direction**. Participation can change instantly.
- **Identities of traders**. L2 and trade data are anonymous.
- **"Smart money" direction**. You cannot see who is on the other side of each trade.
- **Absolute certainty**. Even perfect CVD divergence can fail.

### Crucial Caveats for LMView
- **True trade tape may not be available** for all symbols. The `/api/trades` endpoint returns `data_type` ("exchange_trade" vs "ticker_derived") — always check this field before making order flow claims.
- **Binance reports 24hr taker volume**, not per-trade delta for historical data. To compute CVD, you need the WebSocket trade stream (`trade:latest:*`) which LMView caches with 1-hour TTL.
- **OI data is available only** from perp exchanges (Binance Futures, Bybit, OKX). Spot markets have no OI.
- **L2 order book data can be 30+ seconds stale** when the Flink stream is down and REST fallback is used. Check `freshness` metadata in responses.
- **CVD calculated from cached trade data will drift** from true CVD as trades age out of the cache.

### Always Disclaim
- "Order flow analysis helps us understand current market participation but does not predict future price movements."
- "Large buy walls can be spoofed and canceled. Large sell walls can be icebergs with hidden size."
- "The most reliable order flow setups combine CVD divergence with structure (S/R levels, trend identification) and volume profile context."

---

## 15. References and Further Reading

### Books
- *The Trading Book* by Anne-Marie Baiynd — Practical footprint and tape reading.
- *Mind Over Markets* by James Dalton, Robert Dalton, and Eric Jones — Market Profile theory (foundation of volume profile).
- *Trading in the Zone* by Mark Douglas — Psychology of trading with market structure.
- *Technical Analysis of the Financial Markets* by John J. Murphy — Includes volume analysis.
- *The Misbehavior of Markets* by Benoit Mandelbrot — Fractal nature of markets and why order flow is not predictive.

### Institutional References
- **FINRA** — Rules on spoofing and layering (FINRA Rule 5230, SEC Rule 10b-5).
- **CFTC** — Market manipulation cases involving spoofing in futures markets.

### Trading Platforms and Documentation
- **Jigsaw Trading** — Educational resources on order flow, footprint charts, and tape reading.
- **Sierra Chart** — Footprint chart documentation and volume profile studies.
- **Axiom Index** — Market Profile indicators and educational tools.
- **TradingView** — Volume Profile, CVD, and footprint-style indicators via Pine Script.
- **Binance API Documentation** — Trade and depth stream specifications.

### LMView-Specific
- `lmview_data_caveats.md` — Data freshness and source caveats for all LMView market data.
- `Market_Microstructure.md` — Detailed order book mechanics and market microstructure fundamentals.
- `docs/system/13-caveats.md` — Full inventory of known data pipeline limitations.
