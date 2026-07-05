# On-Chain Analytics — Complete Guide

> **Document Type**: Educational Reference
> **Audience**: AI Assistant, End Users
> **Version**: 0.27.0+
> **Domain**: On-Chain Analysis, Crypto Fundamentals

---

## Table of Contents

1. What Is On-Chain Analysis?
2. Exchange Flows — The Capital Movement Signal
3. Whale Alerts — Large Transaction Tracking
4. Network Value to Transactions (NVT) Ratio
5. Market Value to Realized Value (MVRV) Ratio
6. Spent Output Profit Ratio (SOPR)
7. Network Activity Metrics
   - 7.1 Active Addresses
   - 7.2 New Addresses
   - 7.3 Transaction Count
   - 7.4 Hash Rate (PoW Chains)
   - 7.5 Staking Ratio (PoS Chains)
8. Realized Cap and HODL Waves
9. Miner and Staker Behavior
   - 9.1 Miner Reserves
   - 9.2 Miner-to-Exchange Flows
10. Stablecoin On-Chain Metrics
11. DeFi On-Chain Metrics
12. Market Cycle Indicators
13. Limitations and Caveats
14. References and Further Reading

---

## 1. What Is On-Chain Analysis?

On-chain analysis examines data recorded directly on a blockchain — transactions, wallet addresses, miner activity, and smart contract interactions — to assess the fundamental health and sentiment of a cryptocurrency network.

Unlike price charts that show what the market *thinks* the asset is worth, on-chain data shows what users and holders are *actually doing* with the asset. This makes it a powerful complement to technical analysis.

**Three key categories**:
1. **Capital flows** — Exchange flows, whale movements, stablecoin supply.
2. **Valuation** — NVT, MVRV, realized cap.
3. **Network health** — Active addresses, hash rate, transaction count.

> **Important**: On-chain data is always backward-looking. It tells you what happened, not what will happen. Large wallets move last, and metrics can be manipulated by sophisticated actors.

---

## 2. Exchange Flows — The Capital Movement Signal

Exchange flows track the movement of coins into and out of centralized exchange wallets.

### Inflow Spikes

When large amounts of a coin move **into** exchanges:
- **Interpretation**: Coins are being prepared for sale. Potential sell pressure.
- **Context matters**: A spike during a rally suggests profit-taking. A spike during a crash suggests panic selling.
- **False signal**: Some inflows are just wallet consolidation, staking deposits, or collateral movement.

### Outflow Spikes

When large amounts move **out of** exchanges:
- **Interpretation**: Coins are being withdrawn to cold storage or self-custody. Potential accumulation.
- **Context matters**: Sustained outflows during a downtrend suggests long-term holders are accumulating (bullish). Outflows during a rally also suggests holders are confident and not selling (also bullish).
- **The "exchange supply" metric**: Total coins held on exchanges. When this declines, sell pressure decreases.

### Netflow

Netflow = Inflow − Outflow, smoothed over 7–30 days:
- **Negative netflow** (more outflow than inflow) → Accumulation signal.
- **Positive netflow** (more inflow than outflow) → Distribution signal.
- **Neutral netflow** → Mixed.

**Key exchanges to track**: Binance, Coinbase, OKX, Bybit, Kraken. Each has known wallet clusters identified by on-chain analytics platforms.

---

## 3. Whale Alerts — Large Transaction Tracking

Whale alerts track on-chain transactions above a threshold (typically $100,000 or more).

### Transaction Categories

| Category | Amount | Likely Intent |
|---|---|---|
| OTC trade | $1M–$100M | Large buyer/seller matched off-exchange |
| Exchange deposit | $1M+ | Preparing to sell |
| Exchange withdrawal | $1M+ | Self-custody, accumulation, or staking |
| DeFi interaction | $500K+ | Liquidity provision, yield farming, or liquidation |
| Unknown wallet | $100K+ | Internal transfer between wallets of same owner |

### How to Interpret

- **Whale → Exchange**: Potential sell pressure. The larger the deposit relative to the exchange's daily volume, the bigger the impact.
- **Whale → Unknown wallet**: Self-custody or OTC. Not immediate sell pressure.
- **Recurring same-size transactions**: May be an iceberg or systematic accumulation/distribution.

**Important limitation**: On-chain analytics tools label wallets using cluster analysis, which is imperfect. One "whale" may actually be an exchange's cold wallet, a custodian, or a pooled fund. Always check the wallet's history before drawing conclusions.

---

## 4. Network Value to Transactions (NVT) Ratio

NVT is the on-chain equivalent of the price-to-earnings (P/E) ratio for stocks.

**Formula**:
```
NVT = Market Cap / Daily Transaction Volume (USD)
```

**Developed by**: Willy Woo and Chris Burniske.

### Interpretation

| NVT Value | Signal | Explanation |
|---|---|---|
| > 150 | Overvalued | Network value is high relative to transaction volume. Price may be ahead of utility. |
| 50–150 | Normal | Neutral range. |
| 20–50 | Undervalued | High transaction volume relative to network value. Network has strong utility. |
| < 20 | Potentially undervalued | Extremely high transaction throughput relative to valuation. May signal a bottom. |

### NVT Z-Score

A more refined version: NVT Z-Score measures how far current NVT deviates from its historical mean:

```
NVT Z-Score = (Current NVT − Mean NVT) / Standard Deviation of NVT
```

- **Z-Score > 2** → Significant overvaluation. Market top environment.
- **Z-Score < −2** → Significant undervaluation. Market bottom environment.
- **Z-Score crossing above 3** → Historic tops (2013, 2017, 2021).

### Limitations

- Transaction volume can be inflated by wash trading or dusting attacks.
- Layer 2 transactions (Lightning Network, rollups) are not reflected in L1 on-chain volume.
- Stablecoin transactions can distort NVT because high stablecoin volume doesn't imply BTC/ETH utility.

---

## 5. Market Value to Realized Value (MVRV) Ratio

MVRV compares the current market cap to the "realized cap" — the sum of each coin's value at the price when it last moved.

**Formula**:
```
MVRV = Market Cap / Realized Cap
```

**Developed by**: Coin Metrics, popularized by Murad Mahmudov and David Puell.

### Interpretation

| MVRV | Signal | Historical References |
|---|---|---|
| > 3.5–4.0 | Overvalued | Major top zones (2013, 2017, 2021). Most holders are in significant profit. |
| 2.0–3.5 | Bull market | Healthy range during uptrends. |
| 1.0–2.0 | Transition | Recovery after bear market. |
| 1.0 | Break-even | Average market price equals average cost basis. Important psychological level. |
| < 1.0 | Undervalued | Below cost basis. Bear market bottoms. Typically lasts weeks to months. |

### MVRV Z-Score

An oscillating version used for market cycle timing:

- **Z-Score > 6** → Extreme overvaluation. Near market top. (2013: ~10, 2017: ~12, 2021: ~6)
- **Z-Score 0 to 2** → Bear market bottom zone.
- **Z-Score negative** → Everyone underwater. Extreme bottom.

### Important Nuance

MVRV is most useful for Bitcoin because of its well-established supply distribution. For altcoins, realized cap is less reliable due to:
- Shorter history (less data for Z-score).
- Higher percentage of supply on exchanges (distorts "last moved" calculation).
- Token unlocks and inflation schedules distort realized cap.

---

## 6. Spent Output Profit Ratio (SOPR)

SOPR measures whether coins moved on-chain are being spent at a profit or loss.

**Formula**:
```
SOPR = USD Value of Output / USD Value of Input (when the coin was received)
```

- **SOPR > 1** → The average coin moved was in profit. Sellers are profitable.
- **SOPR < 1** → The average coin moved was a loss. Sellers are capitulating.

### Smoothed SOPR (7-day, 30-day)

Raw daily SOPR is noisy. Smoothing reveals the trend:

| SOPR (7d) | Signal |
|---|---|
| > 1 and rising | Bullish. Profit-taking manageable. Demand absorbing supply. |
| > 1 but falling | Potential top. Profit-taking increasing faster than demand. |
| < 1 and falling | Bearish. Capitation intensifying. |
| < 1 but rising | Potential bottom. Capitation exhausting. |

### SOPR During Cycle Phases

- **Bear market bottom**: SOPR stays below 1 for an extended period (weeks to months). Eventually, it starts recovering as capitulation ends.
- **Bull market start**: SOPR crosses above 1. Early holders start profiting, but demand is strong enough to absorb.
- **Bull market peak**: SOPR spikes to extreme values (> 2–3) with high volume. Then starts declining while price still rises (divergence).
- **Bear market onset**: SOPR drops below 1 quickly as everyone tries to exit.

**aSOPR (Adjusted SOPR)**: Filters out short-term noise by excluding outputs with less than 1-hour coin age. More reliable for trend analysis.

---

## 7. Network Activity Metrics

### 7.1 Active Addresses

Count of unique addresses that participated in transactions during a period (daily active addresses = DAA).

| Condition | Signal |
|---|---|
| Price rising + DAA rising | Organic demand. Sustainable uptrend. |
| Price rising + DAA flat/falling | Speculative. Less sustainable. |
| Price falling + DAA rising | Accumulation. Potential bottom. |
| Price falling + DAA falling | Capitation. Bottom not in. |

**DAA Divergence**: When price makes a new high but DAA makes a lower high, it's a bearish divergence — the rise lacks user adoption. When price makes a new low but DAA makes a higher low, it's a bullish divergence — users are accumulating.

### 7.2 New Addresses

Count of newly created addresses:
- **Rising** → New users entering the ecosystem. Adoption growth.
- **Falling** → Decline in new adoption. Distribution phase.

**Caution**: A single user can create unlimited addresses. New address count is a directional signal, not a precise adoption metric.

### 7.3 Transaction Count

Number of confirmed transactions per day:
- **Rising** → Network utilization growing.
- **Falling** → Network usage declining.
- **Spikes** → Usually associated with high activity (settlements, token distribution, airdrops).

**Limitation**: A high transaction count can be from spam transactions, inscription-related traffic, or low-value transfers. Check the average transaction value for context.

### 7.4 Hash Rate (Proof-of-Work Chains)

Hash rate = total computational power securing the network (primarily Bitcoin).

| Condition | Signal |
|---|---|
| Hash rate rising | Miners are investing in hardware. Network security strengthening. Long-term bullish. |
| Hash rate falling | Miners shutting down. Often follows a major price drop (miner capitulation). |
| Hash rate flat at highs | Healthy. Miners are profitable and staying. |

**Miner capitulation**: When hash rate drops significantly (> 20–30% from ATH) and price is near lows, it often signals the final phase of a bear market. Miners who cannot operate profitably shut down, reducing sell pressure.

### 7.5 Staking Ratio (Proof-of-Stake Chains)

Percentage of circulating supply staked:
- **Rising** → Supply locked. Sell pressure reduced. Usually bullish.
- **Falling** → Supply unlocked (unstaking). Potential sell pressure.
- **Staking yield** → If staking yield is high (> 10%), it may attract capital but also suggests inflation is high.

**Important**: Staking ratio is not always bullish. A high staking ratio with declining active addresses means the asset is becoming a "zombie" — locked but unused.

---

## 8. Realized Cap and HODL Waves

### Realized Cap

The sum of each coin's value at the price when it last moved.

```
Realized Cap = Σ (Each Coin × Price at Last Movement)
```

- **Rising realized cap** → New capital entering at higher prices. Bullish.
- **Falling realized cap** → Capital exiting. Coins being moved at lower prices. Bearish.
- **Realized cap stable while market cap falls** → Coins being held, not sold at a loss. Could indicate a bottom.
- **Realized cap stable while market cap rises** → Unrealized profits accumulating. Could indicate a top.

### HODL Waves

Distribution of coin supply by age since last movement:

| Age Band | Interpretation |
|---|---|
| < 1 day | Highly liquid (exchange activity, active trading). High during volatile periods. |
| 1 week–1 month | Short-term holders. Active trading/speculation. |
| 1 month–1 year | Medium-term investors. |
| 1–2 years | Strong hands. Accumulating through cycles. |
| 2+ years | "HODLers." Long-term believers. Only move during major tops. |
| 5+ years | Lost coins or very long-term holders. Supply that rarely moves. |

**Resurrection**: When old coins (1+ years) start moving → long-term holders selling → potential top signal.
**Hibernation**: When young coins (< 1 month) shrink as a percentage → circulating supply tightening → potential bottom signal.

---

## 9. Miner and Staker Behavior

### 9.1 Miner Reserves

Bitcoin miner reserves — total BTC held by identified mining pools and wallets:

- **Rising** → Miners accumulating. Bullish.
- **Flat or rising during price decline** → Miners are still holding. Not panicking.
- **Falling** → Miners selling to cover costs. Can create sell pressure.
- **Sharp fall during price crash** → Miner capitulation. Often coincides with bear market bottoms.

### 9.2 Miner-to-Exchange Flows

When miners send coins directly to exchanges:
- **High flow** → Immediate sell pressure.
- **Low flow** → Miners are confident in future price.

**Seasonal pattern**: Miners typically sell more after the Bitcoin halving (revenue halves instantly). They accumulate in the months before a halving.

---

## 10. Stablecoin On-Chain Metrics

For stablecoins (USDT, USDC, DAI), on-chain metrics reveal capital flow dynamics:

| Metric | What It Shows |
|---|---|
| **Supply** | Total USDT/USDC in existence. Increasing = new capital entering crypto. |
| **Exchange balance** | Dry powder ready to deploy. |
| **Wallet count** | Adoption of stablecoin as medium of exchange. |
| **Transfer volume** | Usage in actual transactions (not just HODLing). |

**Whale stablecoin flows**: Large USDT/USDC minting events often precede major market moves. When 100M+ USDT is minted on Tron, it's typically deployed into exchanges within days.

---

## 11. DeFi On-Chain Metrics

| Metric | Description | Signal |
|---|---|---|
| **TVL (Total Value Locked)** | Total assets deposited in DeFi protocols | Rising TVL = capital flowing into DeFi. Sector health. |
| **DEX Volume** | Volume on decentralized exchanges | Rising = organic trading activity. |
| **Lending utilization** | % of supplied assets being borrowed | High utilization = high demand for borrowing. |
| **Liquidations** | Value of positions liquidated | Spike in liquidations = market stress. |
| **Protocol revenue** | Fees generated | Rising = protocol sustainability. |

---

## 12. Market Cycle Indicators

Combining on-chain metrics for cycle positioning:

### Top Signals (Multiple Concurrence)
- MVRV > 3.5
- NVT Z-Score > 2–3
- SOPR > 2
- Old coins moving (3y+ HODL wave shrinking)
- Exchange inflow spikes
- Rising stablecoin supply but NOT flowing to exchanges
- DAA declining while price high (bearish divergence)

### Bottom Signals (Multiple Concurrence)
- MVRV < 1.0
- NVT Z-Score < −2
- SOPR < 1 for extended period
- Exchange reserves declining (supply leaving exchanges)
- Hash rate capitulation
- Miners sending to exchanges heavily
- DAA rising while price low (bullish divergence)

### Mid-Cycle Signals (Trend Continuation)
- MVRV between 1.5–3.0
- SOPR oscillating around 1.0–1.5
- Exchange outflows steady
- Hash rate / staking ratio rising
- New addresses and active addresses growing with price

---

## 13. Limitations and Caveats

1. **On-chain data is always backward-looking.** It tells you what happened, not what will happen.
2. **Whales can manipulate.** Large holders can create misleading on-chain patterns (moving coins between their own wallets to create volume).
3. **Labeling is imperfect.** A "whale" wallet identified by analytics may actually be a custodian, exchange, or ETF — not a single individual.
4. **Layer 2 activity is invisible.** Lightning Network, rollups, and sidechains don't appear in L1 metrics.
5. **Privacy coins have limited on-chain data.** Monero, Zcash, and other privacy coins obscure transaction data.
6. **Altcoin history is limited.** MVRV and NVT were designed for Bitcoin. Altcoins with short histories have unreliable Z-score bands.
7. **Token unlocks distort metrics.** A large unlock event can spike exchange inflows and drop SOPR, creating false signals.
8. **Wash trading inflates volume.** Some on-chain volume is artificial, especially on smaller chains.
9. **Data source dependency.** Glassnode, Santiment, CoinMetrics, and Dune differ in methodology. Metrics may not match across platforms.
10. **The AI must not present on-chain signals as definitive trading calls.** Always frame as: "On-chain data suggests X, but these metrics can lag and change."

---

## 14. References and Further Reading

### Key Individuals and Sources
- **Willy Woo** — NVT ratio, on-chain cycle analysis. Blog: Woobull.com.
- **David Puell** — Puell Multiple, MVRV framework. Research on CoinMetrics.
- **Murad Mahmudov** — Bitcoin on-chain macro thesis and MVRV application.
- **William Clemente** — Realized cap, liquidity analysis. Blockware Intelligence.
- **Cole Garner** — On-chain alpha and institutional flow tracking.

### Data Platforms
- **Glassnode** — Most comprehensive on-chain metrics (paid).
- **Santiment** — On-chain + social + development metrics.
- **CoinMetrics** — Professional on-chain data and research.
- **Dune Analytics** — Community-built dashboards for ETH, L2, and DeFi chains.
- **Looker (business)** — In-house BigQuery-based dashboards for exchanges and large holders.

### Books and Reports
- *The Bitcoin Standard* by Saifedean Ammous — Foundation for on-chain value theory.
- *The Bitcoin Renaissance* by Raoul Pal — Macro and on-chain cycle analysis.
- CoinMetrics State of the Network Reports — Quarterly on-chain health.
- Glassnode Weekly Reports — Current cycle positioning with on-chain data.
- Binance Research Reports — On-chain analysis for major altcoins.

### LMView-Specific
- `Correlation_Analysis.md` — Cross-references on-chain metrics with market structure.
- `DeFi_Analysis.md` — DeFi-specific on-chain metrics (TVL, DEX volume, liquidations).
- `Crypto_Fundamentals.md` — Broader crypto fundamentals context.
