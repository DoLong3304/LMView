# Risk Management Frameworks

## Kelly Criterion
- `f* = (bp - q) / b` where:
    - `b` = net odds received on the trade
    - `p` = probability of winning
    - `q` = probability of losing (1 - p)
- **Recommendation:** Use fractional Kelly (25-50%) to reduce volatility
- Full Kelly maximizes growth but has high drawdown risk

## Fixed Fractional Position Sizing
- Risk a fixed percentage of account per trade (typically 1-2%)
- Position size = (account value × risk %) / (entry - stop loss)
- Advantages: simple, scales with account, limits drawdown

## Portfolio Allocation Models
| Model | Allocation | Risk |
|---|---|---|
| Conservative | 5-15% crypto exposure | Low |
| Balanced | 15-30% crypto exposure | Medium |
| Aggressive | 30-60% crypto exposure | High |
| Diversified across 5-10 uncorrelated assets reduces portfolio variance | | |

## Max Drawdown Management
- **Maximum acceptable drawdown:** define before entering trades
- **Circuit breaker:** stop trading for 1-2 weeks after X% drawdown
- **Drawdown recovery requires:** `recovery % = drawdown% / (1 - drawdown%) × 100`

## Risk-Reward Optimization
| Risk:Reward | Win Rate Needed | Notes |
|---|---|---|
| 1:1 | 50% | Break-even before fees |
| 1:2 | 33% | Good for trend-following |
| 1:3 | 25% | Allows many losing trades |
| 1:5 | 17% | Excellent but rare setups |

- **Minimum acceptable RR:** 1:2 for swing trading, 1:1.5 for day trading
- **Scale out:** partial profit taking at different R:R levels
- **Trailing stop:** lock profits as trade moves in your favor
