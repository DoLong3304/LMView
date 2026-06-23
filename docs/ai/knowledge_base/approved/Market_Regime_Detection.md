# Market Regime Detection

## Trending vs Ranging
- Trending markets → use trend-following indicators (MA cross, MACD)
- Ranging markets → use mean-reversion indicators (RSI, Bollinger Bands)
- False signal rate increases when regime is misidentified

## Volatility Regimes (ATR-Based)
- Low ATR (compressed) → breakout imminent
- Expanding ATR → trend acceleration
- High ATR → wide stops, position size reduction

## ADX Usage
- ADX > 25 → trending market (strong trend regardless of direction)
- ADX < 20 → ranging market (use mean-reversion)
- +DI > -DI → bullish trend, -DI > +DI → bearish trend
- ADX rising from low levels → new trend starting

## Chop Index
- Values > 60 → ranging/chop, avoid trend strategies
- Values < 40 → trending, favor trend-following
- Calculated using APO (absolute price oscillator) vs ATR

## Mean Reversion vs Momentum
| Condition | Strategy |
|-----------|----------|
| High ADX + rising ATR | Momentum — ride the trend |
| Low ADX + stable ATR | Mean reversion — fade extremes |
| Low ADX + contracting ATR | Wait for breakout |
| High ADX + extreme RSI | Potential trend exhaustion |
