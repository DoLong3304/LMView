# KNOWLEDGE BASE: GENERAL FINANCIAL KNOWLEDGE AND RISK FOR CRYPTO ANALYSIS / AI AGENT

> **Metadata**: `review_status: approved` | `allowed_for_rag: true` | `internal_only: false`
> **Version scope**: 0.25.x | **Last reviewed**: 2026-06-16


**Important Educational Disclaimer:** This document is solely for educational, research, and analytical system-building purposes. The content is NOT investment advice, a recommendation to buy/sell, personal financial advice, legal advice, or tax advice. Users must take their own responsibility, understand the risks, and consult licensed professionals for personal financial decisions.

**Document Objective:** Standardize concepts of risk/reward, position sizing, diversification, drawdown, volatility, stop-loss, take-profit, risk exposure, scenario analysis, confidence levels, disclaimers, and the strict boundary between analysis and advice for an AI Agent/crypto dashboard.

## Table of Contents
1. Scope, principles, and risk language
2. Risk/reward and expected value
3. Position sizing and capital management
4. Diversification in crypto
5. Drawdown and survival risk
6. Volatility and 24/7 fluctuation
7. Stop-loss, take-profit, and exit plans
8. Risk exposure: measuring total portfolio risk
9. Scenario analysis and stress testing
10. Confidence level: reliability of analysis
11. Educational disclaimer and the difference between analysis and advice
12. Playbook for AI Agent/crypto dashboard
13. Checklist, data schema, and references

## 1. Scope, Principles, and Risk Language
In crypto, general financial knowledge is not just background info; it is the safety layer that prevents the AI Agent from turning market analysis into personalized financial advice.
Users often ask: "Should I buy?", "How much should I enter?", "Where do I put my stop?", or "What leverage?". The system must respond with analytical frameworks, scenarios, risks, assumptions, and educational examples rather than personalized directives.

### Risk Concepts for the Agent:
* **Risk:** The possibility of adverse outcomes deviating from expectations (measured by drawdown, volatility, liquidation risk, counterparty risk). Do not say "safe"; say "relatively lower risk under assumption X".
* **Return:** Expected profit. Do not present target prices as guarantees. Always state invalidation conditions.
* **Uncertainty:** Unknown variables (news, hacks, depegs, legal). Assign low confidence levels when data is missing or markets are erratic.
* **Survival:** The ability to endure drawdowns. In trading, survival is more important than maximizing a single trade. Warn against over-leverage, concentration, and poorly placed stops.

**Core Principle:** A good analysis doesn't just ask "What is the bullish scenario?" It must also answer: Where is it wrong? How much can be lost? What is the confidence level? What conditions invalidate the thesis?

## 2. Risk/Reward and Expected Value
**Risk/Reward (R/R)** is the ratio between the potential reward and potential loss of a trade.
* Risk is measured from Entry to Stop-Loss.
* Reward is measured from Entry to Take-Profit.
Example: Buy BTC at 60k, Stop at 58k, Take-Profit at 66k. Risk = 2k, Reward = 6k. R/R = 3:1.
*This does not mean the trade is guaranteed; it simply means if the scenario is correct, the payout is 3 times the expected loss.*

* **Break-even Win Rate = 1 / (1 + Reward/Risk).** (e.g., A 2:1 R/R requires a 33.3% win rate to break even, ignoring fees).
* **Expectancy = (Win Rate x Average Win) - (Loss Rate x Average Loss).**

### Common Mistakes with R/R:
* **Ignoring probability:** Forcing a 3:1 ratio by setting the target too far and the stop too tight results in a terrible win rate.
* **Ignoring costs:** Funding, slippage, and trading fees heavily impact expected value in crypto futures.
* **Arbitrary stops:** Stops must be based on market structure/invalidation points, not just how much the user wishes to lose.

## 3. Position Sizing and Capital Management
Position sizing determines the size of a trade so that the maximum expected loss stays within the account's risk tolerance.
* **Risk Budget = Account Equity x Risk % per trade.**
* **Spot Position Size = Risk Budget / |Entry - Stop|.**
* **Effective Leverage = Gross Notional / Account Equity.**

### AI Agent Rules for Position Sizing:
* **NEVER suggest a personalized position size.** You do not know the user's financial profile, obligations, or risk appetite.
* **Provide hypothetical examples:** "If a hypothetical account has $10,000 and a 1% risk budget ($100), the position size would be..."
* **Warn about leverage:** If the leverage makes the liquidation price closer than the logical stop-loss, warn the user.
* **Risk is determined by the stop-loss distance, not just the margin used.** Low margin does not mean low risk.

## 4. Diversification in Crypto
Diversification is allocating capital across different assets, strategies, exchanges, and liquidity sources to reduce dependency on a single outcome.
In crypto, diversification is notoriously difficult because altcoins are highly correlated with BTC, liquidity dries up globally during crashes, and systemic risks (stablecoin depegs, exchange bankruptcies) affect the entire market simultaneously.

* **Asset Diversification:** Holding BTC, ETH, stablecoins. (Reduces token-specific risk, but not market-wide crashes).
* **Venue Diversification:** Not keeping all funds on one CEX. Uses cold wallets and multiple exchanges.
* **Fake Diversification:** Holding 10 different AI altcoins is NOT diversification; they will all crash together if the AI narrative fades or BTC drops. Holding spot, perp longs, and staking the exact same token is concentrating risk, not diversifying.

## 5. Drawdown and Survival Risk
**Drawdown** is the peak-to-trough decline in account equity. It measures the real pain an account suffers.
In crypto, 24/7 trading, high leverage, and liquidation cascades can cause massive, rapid drawdowns.
* **Recovery Math:** If you lose 20%, you need a 25% gain to recover. If you lose 50%, you need a 100% gain. If you lose 80%, you need a 400% gain to get back to breakeven.

*Agent Warning for Futures:* Drawdown on an account chart doesn't always reflect liquidation risk. A leveraged position might get liquidated before a valid thesis has time to play out. Monitor liquidation distance, not just PnL.

## 6. Volatility and 24/7 Fluctuation
Volatility is the degree of price variation. Measured via standard deviation, ATR, or high-low ranges.
Crypto trades 24/7, meaning volatility can strike on weekends or holidays when traditional markets are closed and liquidity is thin.

* **Volatility is not purely bad:** Without volatility, trading yields no profit. However, excessive volatility sweeps stop-losses, spikes slippage, and causes liquidations.
* **Agent rule:** High volatility means wider stop-losses are required, which mathematically dictates smaller position sizes to keep the risk budget constant.

## 7. Stop-Loss, Take-Profit, and Exit Plans
* **Stop-Loss:** A mechanism to exit when the thesis is proven wrong.
* **Take-Profit:** A mechanism to lock in gains at target zones.
* **Invalidation-Based Stops:** Stops must answer: "At what price is my original analysis entirely wrong?" (e.g., breaking below a key support).
* **Common Mistakes:** Moving a stop further away as price approaches it (turns small losses into account-destroying losses). Placing stops exactly at obvious round numbers (easily swept by wicks/liquidity hunts).

## 8. Risk Exposure: Measuring Total Portfolio Risk
Risk exposure isn't just margin spent; it is the total notional value at risk, including correlations, stablecoin risk, exchange risk, and liquidity risk.
* **Directional Exposure:** Being net-long on 5 different tokens is a massive single directional bet.
* **Leverage Exposure:** Gross notional value vastly exceeding account equity.
* **Counterparty/Venue Exposure:** Keeping 100% of funds on a single exchange.

## 9. Scenario Analysis and Stress Testing
Evaluating a trade under multiple scenarios rather than predicting a single outcome. Crucial in crypto due to extreme tail risks (exchange halts, depegs, flash crashes).
* **Base Case:** Target PnL, R/R, conditions to hold.
* **Bear Case:** Drawdown, liquidation distance, stop trigger if price drops 10-20%.
* **Stress Case:** What happens if the exchange halts withdrawals? What if slippage triples during a liquidation cascade? What if the stablecoin depegs?

## 10. Confidence Level: Reliability of Analysis
Confidence level refers to the system's trust in data quality, signal confluence, and market regime fit. It does NOT mean "probability of guaranteed profit."
* **High Confidence:** Good data, multiple independent indicators align, clear risk/invalidation levels. ("High confidence in the analysis structure, but outcomes are never guaranteed").
* **Low Confidence:** Missing data, conflicting indicators, extreme macro events pending, illiquid token. ("Signals are mixed/weak; treat this strictly as an observational scenario").

## 11. Educational Disclaimer & Analysis vs. Advice
**Analysis:** Describing data, building scenarios, explaining risks, defining invalidation levels, providing educational formulas.
**Advice:** Recommending a user to buy/sell/short, telling them exactly how much capital to use based on their personal situation.

### Agent Guardrails:
* **Allowed:** "If entry is X and stop is Y, the R/R is 2.5:1 before fees. Risk includes volatility and liquidation."
* **BANNED:** "You should buy this now." / "Use 10x leverage for your account." / "Hold until it hits target Z."

## 12. Playbook for AI Agent / Crypto Dashboard
### Standard Response Structure for Risk Questions:
1. **Context:** State the asset, timeframe, spot/futures, and data used.
2. **Observations:** Price, trend, volatility, volume, funding, OI.
3. **Scenarios:** Provide 2-3 scenarios (Bull/Bear/Range) with activation and invalidation triggers.
4. **Hypothetical R/R:** Calculate risk/reward only using hypothetical numbers.
5. **Major Risks:** Explicitly list volatility, slippage, funding, leverage, and exchange risks.
6. **Confidence Level:** State the confidence level based on data clarity.
7. **Disclaimer:** End with a short educational disclaimer.

## 13. Implementation Checklist and References
* Ensure invalidation points are always clearly defined.
* Check if position size breaches risk budgets.
* Verify liquidation distances for futures trades.
* Assess event risks (CPI, FOMC, unlocks, hacks).
* Monitor for revenge trading or extreme FOMO behavior in user prompts (Agent must defuse and pivot to risk management).
* **References:** SEC Investor.gov, FINRA, CME Group, CFTC Advisories on Virtual Currency Trading.