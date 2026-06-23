# On-Chain Analytics

## Exchange Flows
- **Exchange inflow** spikes → potential sell pressure
- **Exchange outflow** spikes → accumulation, coins moved to cold storage
- **Netflow** (inflow - outflow) smoothed over 7-30 days shows trend

## Whale Alerts
- Transactions > $100K tracked in real time
- Large transfers to exchanges → potential sell
- Large transfers to unknown wallets → OTC or self-custody

## NVT Ratio (Network Value to Transactions)
- NVT = Market Cap / Daily Transaction Volume (USD)
- High NVT (> 100) → overvalued, price detached from network activity
- Low NVT (< 10) → undervalued, high utility relative to price
- Rolling 90-day z-score for mean reversion signals

## MVRV Ratio (Market Value to Realized Value)
- MVRV > 3.5 → historically overvalued, potential top
- MVRV < 1.0 → undervalued, potential bottom
- Z-score bands provide extreme deviation signals

## SOPR (Spent Output Profit Ratio)
- SOPR > 1 → holders selling at profit (potential profit-taking)
- SOPR < 1 → holders selling at loss (capitulation)
- 7-day smoothed SOPR for trend filtering

## Network Metrics
- Active addresses daily → adoption trend
- New addresses created → retail inflow
- Hash rate → mining security + miner sentiment
- Transaction count → network utilization
