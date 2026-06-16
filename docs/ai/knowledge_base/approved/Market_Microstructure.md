# KNOWLEDGE BASE: MARKET MICROSTRUCTURE IN CRYPTO TRADING

> **Metadata**: `review_status: approved` | `allowed_for_rag: true` | `internal_only: false`
> **Version scope**: 0.25.x | **Last reviewed**: 2026-06-16


**Objective:** Provide a clear, actionable foundation for the chatbot/dashboard to explain how orders are placed, matched, suffer slippage, and how to read order book data without over-extrapolating.
**Scope:** Crypto spot and derivative markets on centralized exchanges.
**Warning:** For educational purposes only. Order book signals must not be turned into definitive buy/sell recommendations.

## Table of Contents
1. Overview of Market Microstructure
2. Order book, bid/ask, spread, and depth
3. Liquidity wall, slippage, and execution liquidity
4. Order types (Market, Limit, Stop, OCO, etc.)
5. Aggressive buy/sell, trade flow, and order flow
6. Order book imbalance and dashboard formulas
7. Why the order book is not definitive proof of "whales"
8. Specifics of crypto market microstructure
9. Analysis playbook for AI Agent
10. Data schema, guardrails, and deployment checklist
11. Sample responses for chatbot
12. References

## 1. Overview of Market Microstructure
Market microstructure studies how markets operate at a granular level: how orders enter the system, rest in the order book, match via the engine, how bid/ask prices form, and why market orders cause slippage.
In crypto, it helps answer: "Why did my market order execute at a worse price?", "Is this buy wall reliable?", "Does a bid-heavy order book mean whales are accumulating?", or "Is the spread too wide to trade safely?"
**Core principle:** The order book represents *resting orders* (intentions, which can be canceled). The trade tape/trade flow represents *executed trades* (actual actions). The AI Agent must strictly distinguish between intent and action.

## 2. Order book, bid/ask, spread, and depth
An order book is the ledger of resting limit orders. The **bid side** contains buy orders; the **ask (offer) side** contains sell orders. The highest bid is the **best bid**; the lowest ask is the **best ask**.

### 2.1. Bid / Ask
* **Bid:** The highest price buyers are willing to pay.
* **Ask:** The lowest price sellers are willing to accept.
If someone executes a "market buy", it matches against the ask side. A "market sell" matches against the bid side.

### 2.2. Spread
Spread is the gap between the best ask and the best bid. Narrow spreads mean lower immediate transaction costs. Wide spreads imply higher hidden costs and lower liquidity.
* Absolute spread = Best ask - Best bid.
* Spread in bps = (Best ask - Best bid) / Mid price x 10,000.

### 2.3. Depth
Depth is the volume of resting orders at specific price levels or within a range (e.g., ±1% from mid-price). A market with a narrow spread but thin depth will still cause massive slippage for large orders.
* **L1 depth:** Volume strictly at the best bid and best ask.
* **Cumulative depth:** Total volume across multiple price levels.

### 2.4. L1, L2, L3 Market Data
* Level 1: Best bid, best ask, last traded price.
* Level 2: Multiple price levels with aggregated volume at each level (standard for dashboards).
* Level 3: Individual order granularity, including order IDs.

## 3. Liquidity wall, slippage, and execution liquidity
### 3.1. Liquidity Wall
A liquidity wall is an unusually large cluster of resting orders at a specific price level. A **buy wall** sits below the current price; a **sell wall** sits above.
Walls act as psychological support/resistance, but they are just *resting orders*. They can be canceled, moved, spoofed, or divided.
* **Correct Agent Interpretation:** "There is a large cluster of liquidity at price X. It may act as short-term support if the orders remain when the price approaches."
* **Wrong Agent Interpretation:** "There is a massive buy wall, so whales will definitely defend this price and it will reverse."

### 3.2. Slippage
Slippage is the difference between the expected price and the actual execution price. It occurs with market orders when liquidity is thin or prices are moving rapidly.
Slippage can be positive or negative. For a market buy, executing higher than the reference price is negative slippage.
* Slippage bps = |Execution VWAP - Reference Price| / Reference Price x 10,000.

### 3.4. How to Reduce Slippage
* Use limit orders to control the exact execution price.
* Break large orders into smaller chunks over time (TWAP/VWAP).
* Avoid trading during extreme spread widening, thin depth, API lag, or immediately after news releases.
* Check liquidity across multiple exchanges.

## 4. Order Types
* **Market order:** Executes immediately at the best available price. Guarantees speed, but not price. Highly susceptible to slippage.
* **Limit order:** Executes only at a specified price or better. Can provide liquidity (maker) or take liquidity (aggressive limit). Risk: Might not execute at all.
* **Stop order:** Triggers an order (usually a market order) when a stop price is hit. Risk: Can suffer massive slippage during crashes/wicks.
* **Stop-limit:** Combines a stop price and a limit price. When triggered, it places a limit order. Gives price control but risks non-execution if the price moves too fast.
* **OCO (One-Cancels-the-Other):** Links two orders (e.g., a take-profit limit and a stop-loss). When one executes, the other cancels. Excellent for risk management.

## 5. Aggressive buy/sell, trade flow, and order flow
* **Aggressive buy:** A transaction where the buyer takes liquidity by matching the ask.
* **Aggressive sell:** A transaction where the seller takes liquidity by matching the bid.
* **Trade flow:** The stream of executed trades (price, volume, time, aggressor side).
* **Cumulative Volume Delta (CVD):** The cumulative sum of (Buy volume - Sell volume).
Trade flow is generally more reliable than the order book for confirming actual buying/selling pressure, but it still doesn't reveal trader identities.

## 6. Order Book Imbalance
Imbalance measures the disparity between bid and ask liquidity. If bid depth is much thicker than ask depth, the market may have short-term support. If ask depth is thicker, there may be overhead resistance.
* L1 imbalance = (Bid size - Ask size) / (Bid size + Ask size). Ranges from -1 to +1.
**Agent Warning:** Imbalance is a very short-term, noisy signal. Do not use it to guarantee price direction, as orders can be spoofed or pulled instantly.

## 7. Why the order book is not definitive proof of "whales"
Users often see a massive wall and assume "whales are accumulating." This is a dangerous assumption.
1. **Orders are not executions:** Limit orders can be canceled before they match.
2. **No identity data:** L2 data is anonymous. It could be one whale, many retail users, market makers, or bots.
3. **Hidden/Iceberg orders:** Visible liquidity is not the total liquidity.
4. **Exchange fragmentation:** A wall on Binance doesn't represent Coinbase or OKX.
5. **Spoofing/Layering:** Placing large orders with the intent to cancel them just to create a false illusion of supply/demand is common.
*Safe Response:* "There is a large liquidity cluster, but order book data alone cannot confirm whale activity. We must look for confirmation via executed trade flow, multi-exchange data, and on-chain flows."

## 8. Specifics of Crypto Market Microstructure
* **24/7 Trading:** Liquidity drops during weekends or off-peak hours.
* **Market Fragmentation:** Prices and liquidity for the same asset differ across CEXs, DEXs, and quote pairs (USDT vs USDC).
* **Perpetual Futures Impact:** Funding, liquidations, and mark prices heavily influence short-term order flow.
* **Thin Altcoins:** Wide spreads, thin depth, prone to severe wicks.

## 9. Analysis Playbook for AI Agent
1. **Identify the market:** Spot or perp? Which exchange? Which pair? Snapshot or real-time data?
2. **Check the spread:** Is it wider than usual?
3. **Check depth:** Is there enough depth within ±0.5% to absorb typical orders?
4. **Estimate slippage:** What is the theoretical price impact of a large market order?
5. **Read walls:** Are there massive walls? Do they hold when price approaches, or disappear?
6. **Read trade flow:** Is aggressive buying/selling dominating? Does CVD align with price action?
7. **Conclude cautiously:** State probabilities, note the risks of spoofing, and remind users that resting orders are not executed trades.

## 10. Data Schema and Guardrails
### Mandatory Guardrails for the Agent:
* **NEVER say "whales are buying/selling" based solely on L2 order book data.** Use phrases like "there is a large liquidity cluster."
* **NEVER recommend a trade based purely on imbalance or walls.**
* Always distinguish between visible liquidity (resting orders) and executed volume.
* If data is stale or partial, the Agent must state that the analysis is unreliable.

## 11. Sample Responses for Chatbot
* **"Is this buy wall a whale?"** -> "There is not enough evidence to conclude it's a whale. The order book only shows resting limit orders, which could be market makers, bots, or spoofed orders that might be canceled before execution. We need to see actual trade flow (executions) to confirm buying pressure."
* **"Will my market order suffer slippage?"** -> "Possibly. A market order consumes the opposing side of the order book. If your order size exceeds the liquidity at the best prices, it will execute across multiple price levels, causing slippage. For illiquid pairs, consider a limit order."
* **"Why did the spread widen?"** -> "A widening spread means the gap between the best buy and sell prices has increased. This typically happens during high volatility, low liquidity periods, or immediately following news, increasing your immediate transaction costs."

## 12. References
* Coinbase / Binance / CME Group Developer & API Documentation.
* FINRA / CFTC reports on Spoofing, Layering, and Market Manipulation.
* Academic papers on Order-flow imbalances, Limit Order Markets, and Crypto Wash Trading.