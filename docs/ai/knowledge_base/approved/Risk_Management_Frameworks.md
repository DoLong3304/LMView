# Risk Management Frameworks — Complete Guide

> **Document Type**: Educational Reference
> **Audience**: AI Assistant, End Users
> **Version**: 0.27.0+
> **Domain**: Risk Management, Trading Methodology

---

## Table of Contents

1. Why Risk Management Matters More Than Entry Strategy
2. The Core Risk Management Equation
3. Position Sizing Models
   - 3.1 Fixed Fractional (Most Common)
   - 3.2 Fixed Ratio
   - 3.3 Kelly Criterion
   - 3.4 Optimal f
4. Risk-Reward Ratio (R:R) and Win Rate
5. Drawdown Management
   - 5.1 Maximum Acceptable Drawdown
   - 5.2 Drawdown Recovery Math
   - 5.3 Circuit Breaker Rules
6. Portfolio Allocation Models
7. Stop Loss Placement Strategies
8. Take Profit and Scaling Out
9. Correlation-Based Risk Reduction
10. Risk Management by Market Regime
11. Crypto-Specific Risk Factors
12. Psychological Risk Management
13. Practical Risk Management Workflow
14. Important Caveats and Limitations
15. References and Further Reading

---

## 1. Why Risk Management Matters More Than Entry Strategy

> "The goal of a successful trader is to make the best trades. Money is secondary." — Alexander Elder

Most retail traders focus on entries: finding the perfect pattern, indicator, or signal. But entries alone don't determine profitability. In fact, a trader with a 40% win rate can be highly profitable with proper risk management, while a trader with a 70% win rate can go bankrupt without it.

**The risk management multiplier**: If you risk 2% per trade and have a 40% win rate with 1:3 R:R, you're profitable. If you risk 10% per trade with a 70% win rate and 1:1 R:R, you're one losing streak from blowing up.

**Core principle**: You cannot control the market — you can only control how much you risk. Risk management is the only variable completely within your control.

---

## 2. The Core Risk Management Equation

```
Position Size = (Account Equity × Risk % Per Trade) / (Entry − Stop Loss Distance)
```

**Example**:
- Account: $10,000
- Risk per trade: 2% ($200)
- Entry: $50,000 BTC
- Stop loss: $49,000 (2% price risk)
- Position size = $200 / ($50,000 − $49,000) = 0.2 BTC = $10,000

This means: if stop loss is hit, you lose exactly $200 (2% of account). No more, no less.

**Important**: Stop loss distance must be measured in DOLLARS, not percentages. A 5% stop on a $50,000 BTC is $2,500. If your risk per trade is $200, you cannot use a 5% stop — you must use a 0.4% stop.

---

## 3. Position Sizing Models

### 3.1 Fixed Fractional (Most Common)

Risk a fixed percentage of current account equity on each trade.

| Account Balance | Risk % | $ Risk | Position Size (BTC at $50k, 2% stop) |
|---|---|---|---|
| $10,000 | 2% | $200 | 0.20 BTC |
| $12,000 | 2% | $240 | 0.24 BTC |
| $8,000 | 2% | $160 | 0.16 BTC |

**Pros**: Simple, scales with account, limits drawdown, compound growth.
**Cons**: Size changes with every trade, small accounts have difficulty with precise sizing.

**Risk % guidelines by experience**:
- Beginner: 0.5–1%
- Intermediate: 1–2%
- Advanced: 2–3% (maximum)
- Never exceed 5% per trade

### 3.2 Fixed Ratio

Developed by Ryan Jones. Position size increases/decreases based on a delta ($ per unit increase).

**Formula**: Increase 1 contract/coin for every delta dollars of profit.

**Example**:
- Delta = $5,000 (increase 0.1 BTC exposure per $5K profit)
- Start: 0.1 BTC at $50K, stop 2%
- After $5,000 profit: 0.2 BTC position size

**Pros**: Compounding on profits, conserving capital in drawdowns.
**Cons**: More complex tracking, can over-allocate during winning streaks.

### 3.3 Kelly Criterion

Developed by John Kelly at Bell Labs. Determines optimal bet size to maximize long-term growth:

```
f* = (bp − q) / b
```

Where:
- `b` = net odds received on the trade (R:R)
- `p` = probability of winning
- `q` = probability of losing (1 − p)

**Example** (60% win rate, 1:2 R:R):
- f* = (2 × 0.6 − 0.4) / 2 = 0.8 / 2 = 0.40 (40% of account!)

**Why full Kelly is dangerous**: 40% per trade would cause 80% drawdown during a losing streak. Professional traders use **fractional Kelly** (25–50% of f*).

| Kelly Fraction | Example f* = 40% | Max Drawdown (simulated) |
|---|---|---|
| Full Kelly (100%) | 40% | 80%+ |
| Half Kelly (50%) | 20% | 40% |
| Quarter Kelly (25%) | 10% | 20% |
| Eighth Kelly (12.5%) | 5% | 10% |

**Recommendation**: Use fractional Kelly (25–50%) to balance growth and volatility. Never trade full Kelly.

### 3.4 Optimal f

Developed by Ralph Vince. Similar to Kelly but based on the largest historical loss:

```
f = Max Loss (absolute value) / Account Equity
```

**Example**: If the largest historical loss is $500 on a $10,000 account, f = 0.05 = 5% max per trade.

**Limitation**: Cannot account for larger future losses. Many traders use a fraction of Optimal f (e.g., 25–50%).

---

## 4. Risk-Reward Ratio (R:R) and Win Rate

### Required Win Rate by R:R

| Risk:Reward | Win Rate Needed to Break Even | Win Rate Needed for 20% Return (with 2% risk) |
|---|---|---|
| 1:0.5 | 66.7% | 86.7% |
| 1:1 | 50.0% | 60.0% |
| 1:2 | 33.3% | 40.0% |
| 1:3 | 25.0% | 30.0% |
| 1:4 | 20.0% | 24.0% |
| 1:5 | 16.7% | 20.0% |

**Key insight**: You don't need a high win rate to be profitable. A 1:3 R:R system with 30% win rate is profitable. A 1:1 system with 60% win rate is equally profitable. The choice depends on your personality:

- **High win rate, low R:R** → Mean reversion strategies. Many small wins, occasional large loss.
- **Low win rate, high R:R** → Trend-following strategies. Many small losses, occasional large win.

### Minimum Acceptable R:R by Strategy

| Trading Style | Minimum R:R | Typical Win Rate |
|---|---|---|
| Scalping | 1:1 | 60–70% |
| Intraday | 1:1.5 | 50–60% |
| Swing | 1:2 | 40–50% |
| Position | 1:3 | 30–40% |
| Long-term | 1:5+ | 20–30% |

### Scaling Out

Taking partial profits at different R:R levels improves both win rate and overall R:R:

**Example**: 3-part scale-out on a 1:3 setup:

| Exit | Size | R:R | Outcome |
|---|---|---|---|
| Partial 1 | 33% | 1:1 | 33% of position hits 1R |
| Partial 2 | 33% | 1:2 | 33% of position hits 2R |
| Runner | 34% | 1:3+ | 34% runs for more |

**Win rate boost**: Even if the runner stops out at breakeven, the two partial profits give net positive.

---

## 5. Drawdown Management

### 5.1 Maximum Acceptable Drawdown

Define before you start trading:

| Drawdown | Action |
|---|---|
| 0–10% | Normal. Continue with normal risk. |
| 10–20% | Reduce risk by 50% (1% → 0.5%). Review strategy. |
| 20–30% | Stop trading. Take 1–2 weeks off. Review all recent trades. |
| 30%+ | Major strategy flaw or market regime change. Reset completely. |

**Your max drawdown is determined by your risk % per trade**:

```
Expected Worst Drawdown ≈ Risk % Per Trade × Consecutive Losers × 0.9
```

At 2% risk, a 10-trade losing streak = 20% drawdown.
At 5% risk, a 10-trade losing streak = 50% drawdown (account halved).

### 5.2 Drawdown Recovery Math

To recover from a drawdown, you need a larger percentage gain:

| Drawdown % | Required Return to Breakeven |
|---|---|
| 10% | 11.1% |
| 20% | 25.0% |
| 30% | 42.9% |
| 40% | 66.7% |
| 50% | 100.0% |
| 60% | 150.0% |
| 70% | 233.3% |
| 80% | 400.0% |
| 90% | 900.0% |

**Key insight**: A 50% drawdown requires 100% gain to recover. This is why the first rule of trading is "Don't lose money." Drawdowns compound the difficulty of recovery.

### 5.3 Circuit Breaker Rules

Similar to stock market circuit breakers, but for your own trading:

**Hard rules**:
- After 3 consecutive losses → reduce size by 50%.
- After 5 consecutive losses → stop trading for 1 week.
- After 10% monthly drawdown → stop for the month.
- After any single trade losing > 5% of account → stop for 1 week.
- After any single trade losing > 10% of account → stop for 1 month (strategy review).

**Soft rules**:
- After hitting a personal profit target → take a break (don't overtrade).
- After a large win → reduce size for next 3 trades (regression to mean).
- If feeling emotional (frustration, revenge, euphoria) → stop immediately.

---

## 6. Portfolio Allocation Models

### Total Portfolio Exposure

```
Total Crypto Exposure = % of Net Worth in Crypto
```

| Model | Crypto % | Rest of Portfolio | Risk Level |
|---|---|---|---|
| Conservative | 5–15% | Bonds, cash, real estate | Very low |
| Moderate | 15–30% | Stocks, bonds, real estate | Low |
| Aggressive | 30–50% | Stocks, some alternatives | Medium |
| Full crypto | 50–100% | All in crypto | High |
| Degen | 100%+ (leverage) | Borrowed capital | Extreme |

**General recommendation**: Most investors should keep crypto at 5–30% of total net worth. Going beyond 50% requires understanding that a 70% drawdown is possible.

### Within Crypto Allocation

```
Diversification across market cap and sector
```

| Category | Suggested % of Crypto Portfolio | Purpose |
|---|---|---|
| BTC | 30–60% | Core holding, lowest risk in crypto |
| ETH | 10–25% | Second core holding |
| Top 10 alts | 10–25% | Targeted bets (SOL, etc.) |
| Mid-cap alts | 5–15% | Higher risk, higher reward |
| Small-cap / memes | 0–5% | Speculative; treat as lottery |

**Diversification caution**: Spreading across 50 coins doesn't reduce risk — it increases tracking error. 5–10 uncorrelated coins is sufficient. Holding more than 15 coins becomes impractical to manage and most will correlate anyway.

### The Kelly Portfolio Model

For a portfolio of multiple assets, each with different expected returns and correlations:

```
Allocation per asset = f* × (Expected Return / Variance)
```

This is complex but conceptually simple: allocate more to assets with high expected return and low variance (BTC), less to assets with high variance (small alts).

---

## 7. Stop Loss Placement Strategies

### Price-Based Stops

| Type | Placement | Pros | Cons |
|---|---|---|---|
| **Support/Resistance** | Below most recent swing low | Logic aligned with structure | Wide in volatile markets |
| **Fixed percentage** | Entry − X% | Simple to calculate | May be too tight or too wide |
| **ATR multiple** | Entry − (1.5–3 × ATR) | Adapts to volatility | Can be wide in high vol |
| **MA stop** | Below 50/100/200 MA | Follows trend direction | May get stopped by wicks |
| **Volatility stop** | ATR × Chandelier Exit factor | Adjusts for recent vol | Complex to set |

### Time-Based Stops

| Type | Rule | Use Case |
|---|---|---|
| **Time stop** | Exit if no profit after N bars | Range-bound markets |
| **Session stop** | Exit by end of session | Day trading only |
| **News stop** | Exit before major news | Macro event avoidance |

### Breakeven Stop

Move stop to entry after price moves 1× ATR in your favor. This guarantees no loss on the trade.

```
When: Price reaches Entry + (1 × ATR)
Then: Move stop from original to Entry
```

### Trailing Stop

Move stop as price moves in your favor. Methods:
- **Fixed trail**: Stop trails by fixed distance (e.g., 2× ATR).
- **Parabolic SAR**: Indicator-based trailing stop.
- **Chandelier exit**: Multi-timeframe trailing stop based on ATR.
- **Structure trail**: Stop below the most recent swing low (uptrend) or above most recent swing high (downtrend).

---

## 8. Take Profit and Scaling Out

### Scaling Out Methods

| Method | Description | Best For |
|---|---|---|
| **Equal parts** | Split into 3, exit 33% at each target | General use |
| **Increasing size at runners** | 25% at T1, 35% at T2, 40% runner | Strong trends |
| **Decreasing size at runners** | 50% at T1, 30% at T2, 20% runner | Weak trends, range trades |
| **85% at T1, 15% runner** | Lock most profits, let runner ride | Scalping, tight setups |

### Target Selection

| Target | Placement | Logic |
|---|---|---|
| **T1** | Next swing high/low or 1:1 R:R | Quick confirmation |
| **T2** | Next major S/R level or 1:2 R:R | Medium-term target |
| **Runner** | Break of S/R or 1:3+ R:R | Ride trend if it continues |

**Alternative**: No explicit target — use trailing stop and let the trend decide.

---

## 9. Correlation-Based Risk Reduction

### Portfolio Correlation

If all your positions are highly correlated (all crypto longs), you have not diversified — you have concentrated.

| Portfolio | Correlation | True Risk |
|---|---|---|
| 5 altcoin longs | 0.6–0.9 | Very high (all move together) |
| BTC + ETH + gold | 0.3–0.6 | Moderate |
| Crypto + stock + bonds | 0.1–0.4 | Low |
| BTC long + BTC short | −1.0 | Neutral (hedge) |

**Recommendation**: Ensure your positions don't all correlate. If you're long BTC, ETH, SOL, AVAX, and ADA — you are not diversified. You have five ways to lose when crypto drops.

### Simple Hedging

Hedging reduces risk at the cost of capping upside:

- **Perp short against spot long**: Exposed to funding cost but hedged against price drop.
- **Long BTC, short ETH/alpha**: Neutral the portfolio's alpha net.
- **Outright position reduction vs hedge**: Often better to reduce position and accept lower upside than to hedge and pay funding.

---

## 10. Risk Management by Market Regime

| Regime | Recommended Risk per Trade | Recommended R:R |
|---|---|---|
| **Strong trend** (ADX > 30) | 2% | 1:3+ |
| **Mild trend** (ADX 20–30) | 1.5% | 1:2 |
| **Ranging** (ADX < 20) | 1% | 1:1.5 |
| **High volatility** (ATR > 95th percentile) | 0.5% | 1:2+ (wider stops) |
| **Low volatility** (Band Width squeeze) | 1% | 1:3+ (breakout) |

**Why reduce risk in high vol**: Normal stop distances get picked off by noise. Wider stops mean larger dollar risk per trade, so size must decrease to keep $ risk constant.

---

## 11. Crypto-Specific Risk Factors

### 24/7 Market
- No daily close to reset.
- Weekend liquidation cascades are common (lower liquidity).
- You can wake up to a 20% gap even with a stop.

**Mitigation**: Wider stops on weekends. Reduce position size before sleeping.

### Exchange Risk
- **Exchange downtime**: Binance, Coinbase have suffered outages during high volatility.
- **Withdrawal freeze**: Some exchanges halt withdrawals during crashes.
- **Regulatory shutdown**: US, China, India regulatory actions can freeze assets.

**Mitigation**: Use at least two exchanges. Keep majority of assets in cold/self-custody.

### Liquidity Risk
- **Slippage**: Market orders on illiquid pairs can move 2–5% in one trade.
- **Thin order books**: Alts can gap through stops.

**Mitigation**: Use limit orders. Check order book depth before trading. Avoid illiquid pairs for large positions.

### Funding Rate Risk (Perpetuals)
- **Positive funding**: Longs pay shorts. High positive funding (> 0.1% per 8h) makes long positions expensive to hold.
- **Negative funding**: Shorts pay longs. High negative funding means shorts are expensive.

**Mitigation**: Factor funding into trade cost. Avoid holding positions with extreme funding rates.

### Black Swan Risk
- **Protocol failures**: LUNA collapse (May 2022), FTX (Nov 2022).
- **Regulatory bans**: China ban (Sep 2021), SEC actions.
- **Infrastructure failures**: Chain reorganization, bridge hacks.

**Mitigation**:
- No single position > 10% of portfolio.
- If a position moves > 200%, take at least some profit.
- Maintain a stablecoin reserve (20–30%) for black swan buying opportunities.

---

## 12. Psychological Risk Management

### Emotional State Tracking

| Emotion | Likely Behavior | Action Needed |
|---|---|---|
| **Euphoria** | Overtrading, increasing size, ignoring risk | Reduce size, take profits, step away |
| **Frustration** | Revenge trading, forcing setups | Stop trading for 24 hours |
| **Fear** | Exiting too early, missing good trades | Review plan, trust system |
| **Boredom** | Taking low-quality setups | Reduce screen time, raise entry bar |
| **Confidence (healthy)** | Following plan, accepting losses | Continue, maintain discipline |

### Position Sizing and Emotions

The most common psychological mistake is scaling up after wins and scaling down after losses. The correct behavior is the opposite:

- **After a loss** → Keep size constant (don't revenge trade).
- **After a win** → Keep size constant (don't get overconfident).
- **After a streak** → If you feel on fire, take a break (expect regression to the mean).
- **After a drawdown** → Review methodically: is the strategy broken, or is it just variance?

---

## 13. Practical Risk Management Workflow

### Before Every Trade

- [ ] R:R calculated (minimum acceptable for my strategy)
- [ ] Position size calculated (max risk % × account)
- [ ] Stop loss placed before entry
- [ ] Targets identified (T1, T2, runner plan)
- [ ] Correlation check (is this adding to correlated risk?)
- [ ] Regime check (is my risk level adjusted for current volatility?)
- [ ] Emotion check (am I trading for a good reason?)
- [ ] Current drawdown check (am I within circuit breaker limits?)

### Daily / Weekly Risk Review

- Track: win rate, average R:R, max drawdown, total return.
- Review all losing trades: was it strategy flaw or variance?
- Review all winning trades: did I follow the plan, or get lucky?
- Update position sizing model if account equity changed significantly.

### Monthly Risk Report

| Metric | Target | Current |
|---|---|---|
| Max drawdown | < 15% | |
| Win rate | Depends on strategy | |
| Average R:R | > 2:1 | |
| Risk per trade | 1–2% | |
| Max consecutive losses | Review pattern | |
| Total return | Positive, consistent | |

---

## 14. Important Caveats and Limitations

1. **No risk management system guarantees profit.** Risk management reduces losses, not eliminates them.
2. **Kelly Criterion assumes you know p and b.** In trading, both are estimates. Using incorrect inputs makes Kelly dangerous.
3. **Backtested drawdowns are always smaller than live drawdowns.** Market regimes you haven't seen will produce losses you haven't prepared for.
4. **Position sizing in crypto is imprecise** due to fractional trading, exchange minimums, and liquidity constraints.
5. **Stop losses are not guaranteed in crypto.** During extreme volatility, slippage can exceed your stop distance.
6. **Correlation is not static.** During crises, all correlations approach +1 — diversification fails exactly when you need it most.
7. **Risk management cannot prevent black swans.** LUNA, FTX, and similar events destroyed even well-managed portfolios.
8. **The AI must NOT provide specific position sizes or trade recommendations.** Always frame as: "Risk management principles suggest [general rule]. Individual risk tolerance varies."

---

## 15. References and Further Reading

### Books
- *The New Trading for a Living* by Alexander Elder — Psychology and risk management.
- *Market Wizards* by Jack D. Schwager — Interviews with top traders, many emphasizing risk management.
- *The Black Swan* by Nassim Nicholas Taleb — Why rare events destroy standard risk models.
- *Fooled by Randomness* by Nassim Nicholas Taleb — Why trading results are often luck, not skill.
- *Trade Your Way to Financial Freedom* by Van K. Tharp — Position sizing and expectancy modeling.
- *Portfolio Selection* by Harry Markowitz — Modern portfolio theory foundation.
- *The Kelly Capital Growth Investment Criterion* by MacLean, Thorp, and Ziemba — Complete Kelly reference.

### Academic Papers
- "The Kelly Criterion in Blackjack, Sports Betting, and the Stock Market" by Edward O. Thorp.
- "Portfolio Risk Management" by Campbell R. Harvey — Academic risk management for crypto.
- "Drawdown and Recovery" by Lars Kestner — The math of portfolio drawdowns.

### LMView-Specific
- `Market_Regime_Detection.md` — Adjust risk levels by market regime.
- `Correlation_Analysis.md` — Understand cross-asset and intra-crypto correlation.
- `Derivatives_and_Leverage.md` — Additional risk factors when using leverage or derivatives.
- `General_Financial_Knowledge_and_Risk.md` — Broader financial risk concepts.
