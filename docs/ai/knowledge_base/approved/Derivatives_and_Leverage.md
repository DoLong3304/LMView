# KNOWLEDGE BASE: DERIVATIVES AND LEVERAGE IN CRYPTO TRADING

> **Metadata**: `review_status: approved` | `allowed_for_rag: true` | `internal_only: false`
> **Version scope**: 0.25.x | **Last reviewed**: 2026-06-16


**Objective:** Provide a complete foundation for the AI Agent to explain the crypto derivatives market, specifically perpetual futures, funding rates, open interest, long/short positioning, liquidations, squeezes, and leverage risks.
**Scope:** Centralized exchange crypto derivatives and popular dashboard metrics.
**Warning:** For educational purposes only. The Agent must not turn derivative metrics into definitive trading recommendations, must not encourage high leverage, and must always warn about liquidation risks.

## Table of Contents
1. Overview of derivatives and leverage in crypto
2. Perpetual futures
3. Funding rate
4. Open interest
5. Long/short ratio
6. Liquidation
7. Long squeeze and short squeeze
8. Basis, premium, contango, and backwardation
9. Crowded trade
10. Leverage risk
11. Derivative data reading framework for dashboards
12. Playbook for AI Agent chatbot
13. Data schema and formulas
14. Sample responses
15. Quality control checklist and guardrails
16. References

## 1. Overview of Derivatives and Leverage in Crypto
Derivatives derive their value from an underlying asset (BTC, ETH, altcoins). Popular crypto derivatives include dated futures, perpetual futures, and options. Dashboards heavily focus on perpetual futures because that is where most leverage, funding, open interest, and liquidations occur.
**Leverage** allows users to open a position with a notional value much larger than their margin capital (e.g., 10x leverage = $10,000 position with $1,000 margin). It amplifies both profits and losses, dramatically increasing liquidation risk.
**Core message for the Agent:** In crypto derivatives, price does not solely reflect spot supply/demand. It is heavily influenced by funding rates, margin requirements, forced liquidations, market maker hedging, and leverage chain reactions.

## 2. Perpetual Futures (Perps)
Perpetual futures (perps or perpetual swaps) are derivative contracts with no expiration date. Traders can go long or short without holding the underlying asset. They use a **funding rate** mechanism to anchor the perpetual price to the spot/index price.

### 2.1. Basic Components
* **Index Price:** Aggregate spot price from multiple exchanges.
* **Mark Price:** The fair reference price used by the exchange to calculate unrealized PnL and trigger liquidations (prevents scam wicks from liquidating users based purely on the last traded price).
* **Funding Rate:** Periodic payments between longs and shorts to keep the perp price pegged to the index.
* **Margin & Leverage:** Capital committed vs total position size.
* **Maintenance Margin:** The absolute minimum account balance required to keep a position open before liquidation triggers.

### 2.2. Linear vs. Inverse Perps
* **Linear (USDT/USDC-margined):** PnL and margin are settled in stablecoins. Easier for retail to calculate.
* **Inverse (Coin-margined):** Margin and PnL are settled in the underlying coin (e.g., BTC). Highly risky for longs during downtrends because the collateral value drops concurrently with the position's PnL.

## 3. Funding Rate
Funding is a periodic payment exchanged between longs and shorts. It is not an exchange fee.
* If Perp Price > Spot Price: Funding is positive. Longs pay Shorts. (Incentivizes shorting to push price down).
* If Perp Price < Spot Price: Funding is negative. Shorts pay Longs. (Incentivizes longing to push price up).

### 3.1. Interpreting Funding
* **High Positive Funding:** Strong long demand. Longs are heavily paying to hold positions. The market might be overly bullish or overheated. Trend can sustain it, but reversal/squeeze risks are elevated.
* **Deep Negative Funding:** Strong short demand. Shorts are heavily paying longs. Market is extremely bearish. Potential for a short squeeze if price breaks upward.
* **Funding as a Cost:** Holding a leveraged position against the funding rate slowly drains margin capital over time.

## 4. Open Interest (OI)
Open Interest is the total number of outstanding derivative contracts that have not been settled or closed.
OI differs from Volume: Volume counts all trades executed during a period. OI only counts net open positions.
* **Price UP + OI UP:** New long money entering. Bullish continuation.
* **Price UP + OI DOWN:** Shorts are closing/liquidating (Short covering). Rally might lack new buyers.
* **Price DOWN + OI UP:** New short money entering (or longs absorbing heavy selling).
* **Price DOWN + OI DOWN:** Longs are closing/liquidating (Deleveraging).

*Agent Warning:* OI does not indicate direction. Every contract has one long and one short. High OI simply means high leverage/positioning in the market, increasing the potential for volatility.

## 5. Long/Short Ratio
Measures the ratio between long and short positions.
* **Account Ratio:** Compares the number of accounts net long vs net short. (A small retail account counts the same as a whale).
* **Position/Volume Ratio:** Compares the actual monetary value/size of long vs short positions.
* **Taker Buy/Sell Ratio:** Measures aggressive market buys vs market sells (short-term flow).
*Agent Warning:* A high L/S ratio does not guarantee the price will go up. It often indicates a "crowded trade." If the ratio is heavily long but price drops, a long squeeze is highly likely.

## 6. Liquidation
Forced closure of a position by the exchange when the Margin Balance drops below the Maintenance Margin.
In perps, liquidations turn unrealized losses into forced market orders.
* **Long Liquidation:** Forces a market sell, pushing prices lower.
* **Short Liquidation:** Forces a market buy, pushing prices higher.

### 6.1. Liquidation Cascades
When clustered liquidations trigger one after another. Price drops -> liquidates longs -> forces market sells -> price drops further -> liquidates more longs. This causes massive, rapid wicks on the chart.

### 6.2. Cross vs. Isolated Margin
* **Isolated:** Margin is restricted to a specific position. Limits max loss to that allocated margin but makes that specific position easier to liquidate.
* **Cross:** Uses the entire account balance to prevent liquidation of a single position. A single bad trade can wipe out the entire account balance.

## 7. Long Squeeze and Short Squeeze
* **Long Squeeze:** Price drops rapidly as overcrowded, over-leveraged longs are forced to sell or are liquidated. Often preceded by high positive funding and high OI.
* **Short Squeeze:** Price spikes rapidly as overcrowded, over-leveraged shorts are forced to buy or are liquidated. Often preceded by deep negative funding and high OI.

## 8. Basis, Premium, Contango, and Backwardation
* **Premium:** Futures/Perp Price minus Spot/Index Price.
* **Contango:** Futures price > Spot price. (Market expects higher prices or is paying a premium for leverage).
* **Backwardation:** Futures price < Spot price. (Market is heavily shorting or hedging).
Unlike dated futures, perps do not expire, so basis discrepancies are resolved via the funding rate mechanism rather than settlement delivery.

## 9. Crowded Trade
A situation where too many participants hold the same leveraged position.
* **Crowded Long Risk:** High positive funding + Rising OI + High L/S ratio + Price stalling at resistance.
* **Crowded Short Risk:** Deep negative funding + Rising OI + High L/S ratio (short) + Price holding support despite bad news.

## 10. Leverage Risk
Leverage amplifies PnL sensitivity to price changes.
* 10x leverage means a ~10% adverse price move destroys the initial margin.
* 50x leverage means a ~2% adverse move triggers liquidation.
* 100x leverage means a ~1% adverse move triggers liquidation.
(Actual liquidation happens even sooner due to maintenance margins, funding fees, and trading fees).

## 11. Derivative Data Reading Framework for Dashboards
1. **Healthy Uptrend:** Price rising, OI rising moderately, funding slightly positive, spot volume strong.
2. **Overheated Long:** Price rising fast, OI spiking, funding extremely positive, L/S ratio high. (High risk of long squeeze).
3. **Deleveraging Sell-off:** Price dropping, OI plummeting, massive long liquidations, funding neutralizing.
4. **Bearish Build-up:** Price dropping/sideways, OI rising, funding negative. (Shorts accumulating).

## 12. Playbook for AI Agent Chatbot
### 12.1. Mandatory Rules
1. **Never recommend specific leverage:** Do not say "Use 20x here."
2. **Always state liquidation risks:** Any mention of perps/futures must carry a liquidation warning.
3. **Never use a single metric:** Funding, OI, or liquidations must be contextualized with price action and spot volume.
4. **Do not speculate on whales:** Rising OI or liquidations do not prove what specific "whales" are doing.
5. **Use probabilistic language:** "Risk of a squeeze increases if..." instead of "A squeeze is guaranteed."

### 12.2. Sample Responses
* **"What does high positive funding mean?"** -> "It indicates that longs are paying shorts to hold their positions, usually due to strong long demand driving the perp price above spot. While trends can sustain high funding, extreme levels indicate crowded longs, increasing the risk of a long squeeze if the price drops."
* **"OI is spiking, are whales buying?"** -> "We cannot confirm who is buying. A spike in Open Interest means new derivative positions are being opened (both long and short). To determine market sentiment, we must analyze OI alongside price direction, funding rates, and taker buy/sell ratios."
* **"Is 20x leverage safe?"** -> "20x leverage means your position size is 20 times your margin. An adverse price movement of roughly 5% can entirely wipe out your initial margin, and liquidations happen even sooner due to maintenance margins and fees. Crypto is highly volatile; 20x is considered very high risk. Ensure you understand liquidation prices, funding costs, and use stop-losses."

## 13. Data Schema and Formulas
* `premium_pct = (perp_price - index_price) / index_price`
* `funding_payment = abs(position_notional) * funding_rate`
* `oi_change_pct = (oi_current - oi_previous) / oi_previous`
* `long_short_ratio = long_value_or_accounts / short_value_or_accounts`

## 14. Quality Control Checklist
* Did the Agent verify if the instrument is spot or perpetual?
* Did the Agent differentiate between mark price and last price?
* Did the Agent warn about leverage, liquidation, and funding risks?
* Is the analysis framed as probabilities rather than financial advice?

## 15. References
* Coinbase / Binance / CME Group Educational materials on Funding Rates, Margin, and Futures.
* CFTC Customer Advisories on Virtual Currency Trading.
* Academic papers on Perpetual Futures Pricing and Open Interest in Crypto.