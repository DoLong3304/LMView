# KNOWLEDGE BASE: CRYPTOCURRENCY FUNDAMENTALS

> **Metadata**: `review_status: approved` | `allowed_for_rag: true` | `internal_only: false`
> **Version scope**: 0.25.x | **Last reviewed**: 2026-06-16


**Document Objective:** This document standardizes basic knowledge about crypto assets, exchanges, spot markets, perpetual futures, stablecoins, wallets/custody, exchange risks, liquidity, volatility, market fragmentation, 24/7 trading, and the differences between crypto and traditional markets. This document is written to serve as a knowledge base for the AI Agent: explaining to users, warning of risks, recommending dashboard indicators to display, and avoiding misinterpretations.

**Usage Note:** This document serves educational purposes, product research, and dashboard development. The content does not constitute investment advice, does not recommend buying/selling any crypto asset, and does not replace professional legal, tax, or risk management advice.

## 0. Table of Contents
* 1. How to use this knowledge base for the AI Agent
* 2. What is a crypto asset
* 3. What is an Exchange
* 4. Spot market
* 5. Perpetual futures
* 6. Stablecoin
* 7. Wallet and custody
* 8. Exchange risk
* 9. Liquidity
* 10. Volatility
* 11. Market fragmentation
* 12. 24/7 trading
* 13. Differences between crypto and traditional markets
* 14. Dashboard indicator set to integrate
* 15. AI Agent response playbook
* 16. Answer quality control checklist
* 17. Glossary of terms
* 18. Main references

## 1. How to use this knowledge base for the AI Agent
This knowledge base should be used as the foundational knowledge layer for the chatbot within the crypto dashboard. When a user asks about a term, trading tool, risk, or market metric, the AI Agent needs to answer by providing: a brief definition, operational mechanism, real-world examples, risks, suggested dashboard indicators to observe, and warnings about data limitations.

### 1.1. Response Principles
* **Prioritize explaining the core concept** before giving market opinions. For example: explain what a funding rate is before saying whether a positive or negative funding rate is bullish/bearish.
* **Do not turn the dashboard into a trading recommendation tool.** The Agent can support analysis but should not issue definitive buy/sell commands.
* **Always distinguish between spot, margin, and derivatives.** A question about spot BTCUSDT must not be answered as if it were about BTCUSDT perpetual futures.
* **Always mention custody, liquidity, leverage, volatility, and exchange risks** when users ask about trading or storing assets.
* **Regarding stablecoins, do not use language like 'risk-free' or 'equivalent to bank deposits'.** State that stablecoins attempt to peg their value but still carry depeg, reserve, legal, and operational risks.
* **When explaining wallets, emphasize that crypto is not stored "in" the wallet application;** the wallet manages keys to interact with assets recorded on the blockchain.

### 1.2. Standard Response Structure

| Step | Content the Agent should answer |
|---|---|
| **1. Definition** | Explain the term in 2-4 sentences, avoiding heavy jargon. |
| **2. Mechanism** | State how it works: who participates, how assets/data flow, what factors change the price or risk. |
| **3. Example** | Use examples like BTC, ETH, USDT/USDC, or a popular trading pair like BTC/USDT to illustrate. |
| **4. Risks** | List major risks, especially custody, exchange, liquidity, volatility, leverage, smart contract, and regulatory risks. |
| **5. Dashboard Indicators** | Suggest metrics the user should observe: volume, spread, depth, funding, open interest, TVL, peg deviation, on-chain data. |
| **6. Limitations** | Remind that crypto data is fragmented, varies by exchange, and can be delayed, missing, or distorted by wash trading/fake liquidity. |

### 1.3. What the Agent Should Not Say
* **Do not say:** 'Perpetual futures are like traditional futures but with no expiration.' Clarify that perpetuals have no expiration date and use a funding rate to peg prices to the spot market.
* **Do not say:** 'Wallets store coins.' Clarify: Wallets store/manage keys; assets are recorded on the ledger/blockchain.
* **Do not say:** 'Proof of reserves proves an exchange is safe.' Clarify: Proof of reserves is often just a snapshot of assets at a given time and does not replace full audits of assets, liabilities, and internal controls.
* **Do not say:** 'Stablecoins are always equal to 1 USD.' Clarify: Stablecoins are designed to peg their value but can depeg when reserves, liquidity, or trust weaken.
* **Do not say:** 'Liquidity is high because volume is high.' Must distinguish between volume, order-book depth, bid-ask spread, and slippage.

## 2. What is a Crypto Asset
A crypto asset is a digital asset primarily dependent on cryptography and distributed ledger technology or similar mechanisms. The asset could be a native coin of a blockchain, a token issued via a smart contract, a stablecoin, governance token, utility token, tokenized asset, NFT, or a DeFi-related token. Not all crypto assets share the same valuation logic, economic rights, or legal risks.

### 2.1. Core Technical Components

| Component | Meaning | Dashboard/Agent Display Example |
|---|---|---|
| **Blockchain / Distributed ledger** | Distributed database recording transactions in blocks. Multiple nodes maintain the ledger copy. | Explorer link, chain, block height, transaction confirmation. |
| **Cryptographic keys** | Private keys are used to sign transactions; public keys/addresses to receive and verify. Losing a private key means losing asset control. | Self-custody warnings; never ask users for private keys/seed phrases. |
| **Consensus** | Mechanism for network agreement on the ledger state: Proof-of-Work, Proof-of-Stake, etc. | Consensus type, validator/miner count, staking ratio, hashrate. |
| **Native coin** | Native asset of a chain, used to pay transaction fees and incentivize network security. | ETH on Ethereum, BTC on Bitcoin, SOL on Solana. |
| **Smart contract** | Programs running on the blockchain executing token logic, lending, DEX, staking, bridges, NFTs. | Contract address, audit status, TVL, exploit history. |
| **Token standard** | Technical standards for tokens to interact with wallets, exchanges, DApps (e.g., ERC-20, ERC-721). | Token's chain and contract standard. |

### 2.2. Crypto Asset Classification by Use Case

| Group | Description | Example | Fundamentals Analysis Points |
|---|---|---|---|
| **Cryptocurrency / payment coin** | Assets used as a medium of exchange or store of value in decentralized networks. | BTC, LTC | Network security, supply, adoption, liquidity, decentralization, payment/store of value use case. |
| **Smart contract platform** | Layer 1 or Layer 2 allowing smart contract and DApp deployment. | ETH, SOL, AVAX, BNB | Fee revenue, active users, developer activity, TVL, throughput, fees, roadmap, security. |
| **Stablecoin** | Tokens aiming to maintain a stable price against a reference asset like USD. | USDT, USDC, DAI | Pegging mechanism, reserves/collateral, redemption rights, legal, peg deviation, liquidity. |
| **DeFi protocol token** | Tokens tied to lending, DEX, derivatives, liquid staking, yield, or bridge protocols. | UNI, AAVE, MKR | Fee, revenue, token capture, governance, TVL, volume, smart contract risk, competition. |
| **Governance token** | Tokens used to vote on protocol changes; economic rights may or may not be clear. | COMP, ARB | Voting rights, concentration, treasury, proposal history, value accrual. |
| **Asset-backed / tokenized asset** | Tokens representing off-chain rights or traditional financial assets. | Tokenized T-bills, wrapped assets | Legal structure, issuer, custody, redemption, reserve audit, counterparty risk. |
| **NFT** | Non-fungible tokens, usually representing collectibles, game items, access rights, or certification. | ERC-721 NFT | Uniqueness, community, IP rights, liquidity, royalty, wash trading. |

### 2.3. Distinguishing Coins, Tokens, and Protocols
* **Native coins** are usually issued by the blockchain itself and are required for transaction fees or network security.
* **Tokens** are usually issued via smart contracts on an existing blockchain.
* **Protocols** are systems that provide services, with or without a token.
The Agent must avoid equating a 'good project' with a 'token price increase', as token holder rights may not receive cash flows or ownership like traditional shareholders.

### 2.4. Fundamental Analysis Framework for Crypto Assets

| Analysis Axis | Questions to Answer |
|---|---|
| **Use case** | What problem does the asset solve? Is there real demand or just narrative? |
| **Network adoption** | Are users, transactions, active addresses, developers, TVL, and volume growing sustainably? |
| **Tokenomics** | Current supply/FDV, unlock schedule, inflation, burn, staking, voting rights, utility, and value accrual? |
| **Security** | Has the chain/protocol been hacked? Audited? Are validators/miners centralized? Bridge/oracle risks? |
| **Revenue / fees** | Does the protocol generate fees/revenue? Does revenue accrue to token holders, treasury, or validators? |
| **Governance** | Who controls upgrades, treasury, risk parameters? Is governance centralized around the team/VCs? |
| **Liquidity** | Does the token have real liquidity or just nominal volume? Can positions be exited with low slippage? |
| **Regulatory** | Is the token at risk of being classified as a security, derivative, e-money, or regulated product? |

## 3. What is an Exchange
An exchange in crypto is where users buy and sell crypto assets. It can be a Centralized Exchange (CEX) operated by a company, or a Decentralized Exchange (DEX) operated via smart contracts and on-chain liquidity pools/order books.
Unlike many traditional markets, a crypto exchange can simultaneously act as a broker, matching engine, custodian, lending provider, staking platform, derivatives provider, and market data provider. This vertical integration creates convenience but also conflicts of interest and risks.

### 3.1. CEX vs. DEX

| Criteria | CEX (Centralized Exchange) | DEX (Decentralized Exchange) |
|---|---|---|
| **Operation** | Company operates order book, accounts, matching engine, custody, API, and deposit/withdrawal processes. | Smart contracts handle swaps/orders; users usually trade directly from non-custodial wallets. |
| **Custody** | Usually custodial: the exchange holds private keys or controls assets for the user. | Usually non-custodial: users sign transactions themselves using their wallet. |
| **Liquidity** | Often deeper order books for major coins; professional market makers present. | Depends on liquidity pools, LPs, AMM curves, pool fees, TVL, and incentives. |
| **Main Risks** | Counterparty, bankruptcy, withdrawal halts, commingling, hacks, limited proof-of-reserves, regulatory risk. | Smart contract exploits, oracle/bridge risk, MEV, rug pulls, liquidity drains, phishing. |
| **Data** | Trade data and order books often via exchange API; risk of opacity/wash volume. | On-chain data is more transparent but requires analyzing pools, contracts, and bot/MEV activity. |
| **Best suited for** | Fiat on/off-ramp, high-frequency trading, derivatives, simple user experience. | Self-custody, DeFi, long-tail assets, on-chain trading, contract transparency. |

### 3.2. Common Exchange Functions
* **Spot trading:** Buying/selling base assets (BTC, ETH, SOL) with fiat, stablecoins, or other crypto.
* **Derivatives:** Perpetual futures, dated futures, options, margin trading (carries leverage and liquidation risk).
* **Custody:** Holding assets for clients or supporting hosted wallets.
* **On/off ramp:** Depositing/withdrawing fiat via banks, cards, or stablecoins.
* **Market data:** Prices, order books, volumes, funding rates, open interest, liquidations, index prices.
* **Listing/delisting:** Deciding which tokens trade; heavily impacts liquidity and user risk.
* **Earn/lending/staking:** Lending, staking, yield products; need to distinguish on-chain yields from lending yields and token incentives.

### 3.3. What the Agent should clarify when users ask about an "Exchange"
* Are they asking about a CEX or a DEX?
* Do they want to trade spot, margin, or perps?
* Are they looking for long-term storage or short-term trading?
* Are they focused on fees, liquidity, safety, legal compliance, or analytical tools?
* What is their jurisdiction? (Some services are geo-restricted).

## 4. Spot Market
The spot market is where assets are bought and sold for immediate (or near-immediate) delivery and settlement. Spot trading means buying/selling the underlying asset (e.g., BTC, ETH) in trading pairs like BTC/USDT. After execution, the asset balance updates in the exchange account or on-chain if withdrawn.

### 4.1. Trading Pair Structure

| Concept | Explanation | Example |
|---|---|---|
| **Base asset** | The asset being bought/sold. | In BTC/USDT, BTC is the base asset. |
| **Quote asset** | The asset used to price the base asset. | In BTC/USDT, USDT is the quote asset. |
| **Bid** | The highest price buyers are willing to pay. | A bid of 65,000 USDT means someone wants to buy BTC at 65,000. |
| **Ask** | The lowest price sellers are willing to accept. | An ask of 65,010 USDT means someone wants to sell BTC at 65,010. |
| **Spread** | The gap between ask and bid. A narrow spread usually indicates better liquidity. | Ask 65,010 - Bid 65,000 = spread of 10 USDT. |
| **Order book depth** | The volume of buy/sell orders at price levels around the current price. | Depth ±1% shows how much USD liquidity exists within a 1% range. |

### 4.2. Basic Order Types

| Order Type | How it Works | Risks/Notes |
|---|---|---|
| **Market order** | Executes immediately at the best available price in the order book. | Prone to slippage if the order book is thin or the order is large. |
| **Limit order** | Executes only at a specified price or better. | May not execute if the market never reaches the target price. |
| **Stop order** | Triggers an order when the price hits a stop condition. | Can experience heavy slippage during rapid price movements. |
| **Post-only** | Ensures the order only adds liquidity (maker), avoiding taker fees. | Cancelled if it would execute immediately against resting orders. |
| **TWAP/VWAP** | Splits a large order over time/volume. | Reduces market impact but carries execution risk. |

### 4.3. Risks in the Spot Market
* No liquidation risk (unlike futures, if no margin is used), but there is still price depreciation risk, illiquidity, withdrawal halts, hacks, or delistings.
* High 24h volume does not always equal good liquidity. The Agent should check depth, spread, and slippage.
* Spot prices across exchanges can differ due to market fragmentation, withdrawal/deposit fees, geo-restrictions, quote stablecoin differences, and depth.
* On DEXs, users face slippage, MEV/sandwich attacks, high gas fees, contract bugs, or fake tokens.

### 4.4. Dashboard Metrics for Spot
* Spot prices per exchange and volume-weighted average aggregated prices.
* Bid-ask spread, depth ±0.5%, ±1%, ±2%, estimated slippage for a theoretical order size.
* 24h volume, number of supporting exchanges, volume distribution across exchanges.
* Alerts for liquidity heavily concentrated in a single exchange or DEX pool.
* Alerts for abnormal price differences across exchanges (CEX vs. DEX).

## 5. Perpetual Futures
Perpetual futures (perps) are derivative contracts with no expiration date. Traders can open long or short leveraged positions without owning the underlying asset. To keep the perpetual price pegged to the spot/index price, perps use a **funding rate**.
If the perpetual price > spot price, funding is usually positive (longs pay shorts). If the perpetual price < spot price, funding is usually negative (shorts pay longs).

### 5.1. Core Mechanisms

| Concept | Explanation | Why it matters |
|---|---|---|
| **Index price** | Aggregate reference price from multiple spot exchanges. | Reduces the ability of a single exchange to manipulate liquidation prices. |
| **Mark price** | The price used to calculate unrealized PnL and liquidations. | Users can be liquidated based on mark price even if the last traded price differs. |
| **Funding rate** | Periodic payments between longs and shorts. | Indicates position pressure and cost of holding; prolonged high funding suggests crowded trades. |
| **Open interest (OI)** | Total value of outstanding open positions. | Rising OI with rising price suggests new money; extremely high OI increases liquidation cascade risks. |
| **Leverage** | Amplifies exposure relative to margin capital. | Increases potential profit but drastically increases liquidation risk. |
| **Maintenance margin** | Minimum margin required to keep a position open. | If margin falls below this, the position is liquidated. |
| **Liquidation** | Forced closure of a position by the exchange when margin is insufficient. | Can create chain reactions (cascades) during high volatility. |

### 5.2. Perpetual Futures vs. Traditional Futures

| Criteria | Perpetual Futures | Traditional Dated Futures |
|---|---|---|
| **Expiration** | No fixed expiration date. | Has a specific expiration/settlement date. |
| **Pegging Mechanism** | Periodic funding rate between long and short. | Price converges to spot upon expiration via delivery/settlement. |
| **Rollover** | No need to roll over. | Must roll over to a new contract to maintain exposure. |
| **Specific Risks** | Funding volatility, liquidation cascades, mark/index manipulation, auto-deleveraging. | Basis risk, rollover risk, margin calls, liquidity gaps by term. |

### 5.3. Risks of Perps
* Leverage accelerates losses. Even a tiny fluctuation can liquidate high-leverage accounts.
* Funding rates aren't fixed interest; they can flip signs and spike during one-sided markets.
* Last price, mark price, and index price differ. Users must know which triggers stops/liquidations.
* Liquidation cascades can cause extreme price wicks when OI is high and order books are thin.
* Low-cap altcoin perps have worse liquidity, worse index quality, and higher manipulation risks.
* Auto-deleveraging (ADL), insurance funds, and risk engines vary by exchange.

### 5.4. Dashboard Metrics for Perps
* Current, predicted, and historical funding rates, plus funding ranking across exchanges.
* Open interest (in USD and tokens), OI changes (1h/4h/24h).
* Basis between perpetual price and spot/index price.
* Long/short ratios, liquidation data, liquidation heatmaps/clusters.
* Mark price, index price, last price, maintenance margin, max leverage per exchange.
* Alerts for extreme funding, rapid OI spikes, volume drops, or worsening spread/depth.

## 6. Stablecoin
Stablecoins are crypto assets designed to maintain a stable value against a reference asset, usually USD. They serve as quote currencies, exchange transfer mediums, DeFi collateral, and fiat-crypto bridges.
However, 'stable' does not mean risk-free. Stablecoins can depeg, face redemption limits, reserve risks, regulatory risks, operational risks, smart contract risks, and crises of confidence.

### 6.1. Types of Stablecoins

| Type | Pegging Mechanism | Main Risks | Concept Example |
|---|---|---|---|
| **Fiat-backed** | Issuer holds reserves (cash, bank deposits, T-bills) to back 1:1 redemptions. | Reserve quality/transparency, redemption rights, bank/custodian risk, legal, freeze/censorship. | USDT, USDC |
| **Crypto-collateralized** | Collateralized by other crypto, usually over-collateralized, relying on liquidations if collateral drops. | Collateral volatility, oracle failures, liquidation cascades, smart contract risks. | DAI, lending-vault models |
| **Commodity-backed** | Backed by physical assets like gold. | Custody of physical assets, audits, storage fees, redemption rights. | Gold tokens |
| **Algorithmic / seigniorage** | Uses algorithms or mint/burn incentives to maintain peg, without full reserves. | Bank runs, death spirals, loss of trust, thin liquidity, failed incentive design. | Failed models from past cycles |
| **Yield-bearing** | Wrapper or stablecoin generating yields from T-bills or DeFi. | Yield source, duration risk, counterparty, smart contracts, securities regulations. | Tokenized cash/yield vaults |

### 6.2. Peg Maintenance Mechanisms
* **Reserve backing:** Issuer pledges sufficient high-quality assets to back circulating supply.
* **Redemption:** Eligible users can redeem stablecoins for the reference asset (USD).
* **Arbitrage:** When trading < $1, arbitrageurs buy cheap and redeem; when > $1, they mint and sell.
* **Over-collateralization:** Crypto-backed stablecoins hold more collateral than issued stablecoins to absorb volatility.
* **Liquidation:** If collateral falls below a threshold, the system liquidates it to protect the peg.
* **Oracles:** DeFi stablecoins rely on price feeds; faulty oracles cause bad liquidations or peg loss.

### 6.3. Stablecoin Tracking Metrics

| Metric | Meaning | Warning |
|---|---|---|
| **Peg deviation** | Price difference from 1 USD or reference. | Prolonged deviations > 0.5%-1% warrant alerts. |
| **Supply** | Total circulating stablecoins. | Rapid supply drops may indicate heavy redemptions/liquidity drain. |
| **Reserve composition** | Share of cash, T-bills, repo, commercial paper, crypto. | Risky/illiquid reserves increase bank run risks. |
| **Redemption terms** | Who can redeem, minimums, timelines, fees. | If retail cannot redeem directly, secondary market prices dictate value. |
| **Chain distribution** | Which chains the stablecoin operates on. | Bridges/wrapped versions increase technical risks. |
| **DEX/CEX liquidity** | Depth of stablecoin pools and order books. | Severely imbalanced pools signal selling pressure or loss of trust. |

### 6.4. Agent Playbook: "Is this stablecoin safe?"
The Agent should not just say "safe" or "unsafe". It must analyze peg design, reserve/collateral quality, redemption rights, and operational/legal risks.
*Warning Example:* "Stablecoins are designed to peg their value but are not bank deposits and are not risk-free. Before holding a stablecoin or using it as collateral, review its backing mechanism, redemption rights, reserve transparency, historical depegs, active chains, and liquidity on exchanges."

## 7. Wallet and Custody
A wallet is a tool to interact with blockchain accounts: viewing balances, signing transactions, sending/receiving, connecting to DApps, and managing identity. Wallets do not "store coins" like physical wallets; assets are on the blockchain, while the wallet manages the keys to prove control.
**Custody** refers to who controls the keys. Self-custody (non-custodial) means the user holds the keys. Custodial means a third party (like an exchange) holds the keys.

### 7.1. Keys, Addresses, and Seed Phrases

| Concept | Explanation | Risk if misunderstood |
|---|---|---|
| **Private key** | Cryptographic secret used to sign transactions and prove control. | Exposed private key = someone else can drain your assets. |
| **Public key** | Derived from the private key, used to verify signatures. | Do not use as a private key; privacy precautions still apply. |
| **Address** | Identifier for receiving assets, usually derived from a public key/contract. | Sending to the wrong chain/address can result in permanent loss. |
| **Seed phrase** | Recovery phrase used to regenerate private keys in HD wallets. | Lost seed = lost recovery ability; exposed seed = lost assets. |
| **Signature** | Digital signature confirming the key controller approved a transaction/message. | Signing malicious approvals can drain tokens. |
| **Approval** | Allowing smart contracts to spend tokens on your behalf. | Unlimited approvals on malicious contracts are massive risks. |

### 7.2. Custody Models

| Model | How it Works | Pros | Risks |
|---|---|---|---|
| **Custodial exchange** | Exchange holds keys and credits internal balances to users. | Easy to use, KYC recovery, fast trading, fiat ramps. | Counterparty risk, bankruptcies, withdrawal halts, hacks, lack of traditional banking protections. |
| **Non-custodial hot wallet** | User holds keys on an internet-connected device. | Full asset control, fast DeFi interaction. | Phishing, malware, bad signatures, lost seeds, compromised devices. |
| **Hardware/cold wallet** | Keys stay offline; transactions signed securely. | Reduces internet hack risks; great for long-term storage. | Lost device/seed, fake devices, user errors, bad signature approvals. |
| **Multisig** | Requires multiple signatures from different keys to move funds. | Removes single points of failure; good for teams/treasuries. | Complex management, losing multiple keys, misconfigurations. |
| **MPC custody** | Keys split into computation shares; no single party holds the whole key. | Good for institutions, decentralized control, policy engines. | Vendor reliance, operational complexity, costs. |
| **Smart contract wallet** | Accounts controlled by smart contracts (account abstraction). | Flexible, supports recovery and spending limits. | Smart contract bugs, upgrade/admin risks, limited chain support. |

### 7.3. Safety Rules the Agent Must Enforce
* Never ask users for private keys, seed phrases, keystores, or 2FA codes.
* Remind users to double-check addresses, chains, memos/tags, and send test transactions first.
* Remind users to verify official wallet domains and beware of phishing sites.
* When connecting DApps, verify approvals, contract audits, and revoke unnecessary allowances.
* Suggest keeping short-term trading funds on exchanges but moving long-term holdings to cold storage based on risk appetite.
* Emphasize that self-custody removes customer support for lost passwords/seeds.

## 8. Exchange Risk
Exchange risk encompasses the risks of trading or storing assets on an exchange. This includes insolvency, hacks, withdrawal halts, commingling of customer funds, conflicts of interest, market manipulation, system outages, opaque proof-of-reserves, and jurisdictional regulatory risks.

### 8.1. Exchange Risk Matrix

| Risk | Description | Warning Signs | Mitigation |
|---|---|---|---|
| **Counterparty / insolvency** | Exchange lacks assets or cannot pay debts. | Withdrawal halts, weird spreads, liquidity rumors, proof-of-reserves lacking liabilities. | Don't keep all funds on one exchange; prefer regulated, audited venues with segregated assets. |
| **Custody risk** | Exchange controls private keys/omnibus wallets. | Opaque cold storage policies, unclear insurance/segregation in Terms of Service. | Withdraw long-term holdings to self-custody or professional custodians. |
| **Operational risk** | System outages, API lag, matching engine failures. | Frequent downtime during volatility, latency, data inconsistencies. | Use limit orders, appropriate stops, avoid max leverage, keep backup venues. |
| **Market integrity** | Wash trading, spoofing, front-running, manipulation. | High volume but thin depth; extreme price wicks; shady token listings. | Cross-check data, use reputable exchanges, avoid illiquid tokens. |
| **Conflict of interest** | Exchange acts as market maker, lender, and token lister simultaneously. | Lack of disclosures on affiliate market makers or loan books. | Prefer venues with clear disclosures, separated operations, and governance standards. |
| **Regulatory risk** | Exchange or product banned in a specific region. | Market exit announcements, ToS changes, regulatory warnings. | Monitor local laws, avoid prohibited services, prepare withdrawal plans. |
| **Cybersecurity** | Hacks of hot wallets, API keys, phishing, SIM swaps. | History of hacks, weak account security. | Use hardware 2FA, whitelist addresses, restrict API permissions, cold storage. |

### 8.2. Proof of Reserves is NOT Enough
Proof of reserves (PoR) is a useful signal but not a full financial audit. An on-chain snapshot of assets doesn't reveal total liabilities, off-balance sheet debts, pledged assets, related-party loans, or if assets were moved right after the snapshot.
* Must review both assets and liabilities.
* Must have clear audit frequency, scope, and independent assurance.
* Must clarify whether customers own the assets or are just general creditors in bankruptcy.
* Must verify if customer assets are lent out, staked, or rehypothecated.

## 9. Liquidity
Liquidity is the ability to buy/sell assets at the desired size without causing massive price shifts or incurring huge transaction costs. In crypto, liquidity is fragmented: a token might be liquid on one exchange but illiquid on another, or liquid against USDT but illiquid against BTC.

### 9.1. Liquidity Metrics

| Metric | Meaning | Weakness if used alone |
|---|---|---|
| **24h Volume** | Total traded value in 24 hours. | Can be manipulated via wash trading, concentrated on one exchange, or fail to reflect current depth. |
| **Bid-ask spread** | Immediate cost between best buy and sell. | Narrow spreads with thin depth still cause massive slippage for large orders. |
| **Order book depth** | Available volume around the current price (e.g. ±1%). | Depth can vanish quickly (pulled orders) during volatility. |
| **Slippage** | Execution price worse than expected due to order size/thin books. | Estimates depend on snapshots and differ when the market is moving fast. |
| **Market impact** | Price movement caused specifically by your trade. | Hard to measure without tick-level order book data. |
| **Turnover** | Volume / Market Cap. | Market cap can be misleading due to unclear circulating supply. |
| **TVL / pool depth** | In DEXs/AMMs, locked assets dictate swap capability. | High TVL doesn't guarantee low slippage if the pool is imbalanced or gas fees are high. |
| **Exchange concentration** | Share of volume/depth across major exchanges. | High concentration means severe risks if that single exchange halts trading. |

### 9.2. Conditions for Good Liquidity
* Real, stable volume across multiple exchanges, not just temporary spikes.
* Narrow spreads and thick depth on both bid and ask sides.
* Multiple independent market makers or liquidity sources.
* Not entirely dependent on a single stablecoin, DEX pool, or exchange.
* Large trades do not permanently displace the price far from reference averages.
* Liquidity does not instantly vanish during market stress.

### 9.3. Agent Playbook: Explaining Liquidity
*Sample Response:* "A token with $100M 24h volume might not have good liquidity if 90% of that volume is on an opaque exchange, or if the order book depth within ±1% is only $200k. To properly assess liquidity, look at volume, spread, depth, simulated slippage, number of supported exchanges, and liquidity concentration simultaneously."

## 10. Volatility
Volatility measures the degree of price fluctuation. Crypto typically has high volatility due to 24/7 trading, fragmented liquidity, high leverage, constant news flow, smaller market sizes compared to traditional assets, regulatory risks, and tokenomic structures (unlocks, burns).
Volatility creates trading opportunities but requires strict risk management (sizing, stops, leverage limits).

### 10.1. Types of Volatility

| Type | Explanation | Dashboard Application |
|---|---|---|
| **Historical/Realized** | Past volatility calculated from actual returns. | 7D/30D/90D volatility, rolling vol, percentile rank. |
| **Implied volatility** | Market's expectation of future volatility, derived from options. | Options market tracking, vol surfaces, skews. |
| **Intraday volatility** | Fluctuations within the day/hour. | Alerts for abnormal trading hours behavior. |
| **Event volatility** | Spikes around listings, unlocks, hacks, FOMC/CPI news. | Event calendars, abnormal returns, volume spikes. |
| **Cross-asset volatility** | Correlations between BTC, ETH, altcoins, USD/equities. | Correlation heatmaps, beta to BTC, dominance metrics. |

### 10.2. Causes of Crypto Volatility
* Leverage and liquidation cascades: forced closures cause chain-reaction buying/selling.
* Extreme funding rates: crowded long/short trades reverse violently.
* Thin weekend liquidity.
* Macro news, hacks, regulatory actions, ETF flows.
* Token unlocks, airdrops, emissions.
* Infrastructure risks (chain halts, bridge exploits, gas fee spikes).
* Narrative rotations (capital shifting rapidly between AI, DeFi, Memes, L1s).

### 10.3. Agent Playbook: Warning about Volatility
* Never treat high volatility alone as an independent buy/sell signal.
* If volatility rises alongside extreme OI and funding, warn about squeeze/liquidation risks.
* If volatility rises but volume/depth drops, warn about slippage and widening spreads.
* For small tokens, check for specific events (listings, unlocks, rumors).
* For stablecoins, even minor volatility matters since the peg expectation is incredibly tight.

## 11. Market Fragmentation
Market fragmentation occurs when liquidity, prices, data, and trading activity are split across multiple exchanges, chains, trading pairs, stablecoin quotes, jurisdictions, and product types (spot, perps, DEXs). Unlike traditional equities with consolidated tapes, crypto is highly dispersed.

### 11.1. Layers of Fragmentation

| Layer | Description | Consequences |
|---|---|---|
| **Venue** | Same asset traded on various CEXs/DEXs with different fees/rules. | Price discrepancies, arbitrage, inconsistent depth data. |
| **Pair** | Traded against USDT, USDC, USD, BTC, ETH. | Fractured liquidity; prices depend on the quote asset's own stability. |
| **Chain** | Asset exists on multiple chains or as wrapped tokens. | Bridge risks, contract risks, sending to wrong chains. |
| **Product** | Spot, margin, perps, dated futures, options. | Spot and derivative prices diverge; funding reflects specific derivative pressure. |
| **Regulatory** | Different rules per country. | Geo-blocked services, regulatory arbitrage, forced account closures. |
| **Data** | Different sources report different volume, market cap, supply, OI. | Dashboards may show false signals if data is not normalized. |

### 11.2. Impact on AI Agent and Dashboard
* Never grab a single price from one small exchange and claim it is the "global market price".
* Always state the data source, update time, pair, and exchange/chain.
* Use volume-weighted composite prices when possible.
* If identifying large arbitrage, warn that it might not be actionable due to withdrawal fees, chain congestion, KYC limits, withdrawal halts, or stablecoin risks.
* Verify contract addresses on DEXs to avoid fake tokens.

### 11.3. Dashboard Fragmentation Modules
* Exchange volume share (dominance per venue).
* Pair distribution (USDT vs USDC vs USD).
* CEX vs. DEX price differences and slippage simulators.
* Chain distribution of token supply/liquidity.
* Deposit/withdrawal status per exchange.
* Data quality scores (number of sources, freshness, outliers).

## 12. 24/7 Trading
Crypto operates nearly 24 hours a day, 7 days a week, unlike traditional equities which have standard sessions, weekends, and holidays. While this allows instant reactions to global news, it severely complicates risk management, as volatility can strike while users sleep, during low-liquidity hours, or when traditional markets are closed.

### 12.1. Consequences of a 24/7 Market

| Consequence | Explanation | Agent Warning |
|---|---|---|
| **Weekend gap in TradFi vs crypto** | Crypto trades while stocks/bonds are closed. | Weekend news creates massive crypto volatility before TradFi opens. |
| **Varying liquidity by hour** | Not all hours have equal market maker presence and volume. | Large market orders during off-peak hours face terrible slippage. |
| **Sleep risk for leveraged traders** | Positions can be liquidated overnight. | "Use stop-losses, margin buffers, and price alerts." |
| **Funding windows** | Perp funding often calculates in 8-hour cycles. | Do not interpret funding statically; watch historical trends and timing. |
| **Cross-market reactions** | Crypto reacts to macro events before other markets open. | Do not analyze crypto in a vacuum without looking at USD/macro liquidity. |

### 12.2. 24/7 Dashboard Alerts
* Alerts for price movements exceeding thresholds in 1h/4h/24h windows.
* Alerts for sudden spread or slippage spikes.
* Alerts for abnormal funding/OI spikes during low-liquidity hours.
* Alerts for stablecoin depegs.
* Alerts for exchange withdrawal halts or blockchain congestion.
* "Night risk summaries" for users holding positions overnight/weekends.

## 13. Differences Between Crypto and Traditional Markets
Both share concepts like prices, liquidity, order books, derivatives, and market makers. However, crypto differs fundamentally in infrastructure, custody, settlement, trading hours, cross-border nature, investor protections, data, token issuance, and smart contracts.

| Criteria | Crypto Markets | Traditional Markets (TradFi) |
|---|---|---|
| **Infrastructure** | Runs on blockchains/DLTs; trades on-chain or via internal exchange ledgers. | Centralized infrastructure: stock exchanges, brokers, clearing houses, CSDs. |
| **Custody** | Users can self-custody via private keys or use exchanges/custodians. | Investors hold assets via brokers/custodians within clear legal frameworks. |
| **Settlement** | On-chain settlement is near real-time; CEXs settle internally and batch on-chain withdrawals. | Standard settlement cycles (T+1/T+2) via clearing systems. |
| **Trading hours** | 24/7/365, with occasional exchange maintenance. | Fixed trading sessions, weekends, holidays, opening/closing mechanisms. |
| **Derivatives** | Perpetual futures dominate; funding rates and auto-liquidations are central. | Dated futures/options dominate; standardized margin rules via clearing houses. |
| **Investor protection** | Varies widely; many platforms lack SIPC/FDIC equivalent protections or clearing houses. | Regulated markets have asset segregation, capital requirements, and strict oversight. |
| **Data transparency** | Fragmented by exchange/chain; supply/volume data varies by provider. | Standardized via exchanges, consolidated feeds, and regulatory filings. |
| **Valuation** | Many tokens lack direct cash flows; relies on tokenomics, network usage, governance, liquidity. | Stocks/bonds have financial statements, cash flows, and clear legal credit claims. |
| **Tech risk** | Smart contract bugs, bridge hacks, oracle failures, chain halts, lost keys. | Tech risks exist but usually aren't tied directly to the asset's core logic. |
| **Transparency** | On-chain data is highly transparent, but off-chain exchange liabilities and user identities are opaque. | Off-chain data is less granular per trade but corporate reporting and audits are highly transparent. |

### 13.1. Mistakes When Applying TradFi Thinking to Crypto
* Treating an exchange account like an insured bank account (it is not).
* Treating stablecoins as risk-free USD (they carry issuer/reserve risks).
* Equating token market cap with equity market capitalization (tokens don't always confer ownership).
* Viewing token holders as shareholders (governance tokens often lack legal rights to cash flows).
* Assuming high volume equals deep liquidity (crypto volume can be wash traded; must verify order books).
* Treating perps exactly like traditional futures (perps do not expire and use funding rates).

## 14. Dashboard Indicator Set to Integrate

| Group | Metric | Purpose |
|---|---|---|
| **Market** | Price, market cap, FDV, circulating/total/max supply, dominance. | Assess scale and valuation context. |
| **Liquidity** | 24h Volume, bid-ask spread, depth ±1%, slippage simulation, exchange concentration. | Assess actual tradability. |
| **Derivatives** | Funding rate, open interest, basis, liquidations, long/short ratio, options IV/skew. | Assess leverage, crowded trades, squeeze risks. |
| **Stablecoin** | Peg deviation, supply, reserve composition, redemption terms, pool balances, chain distribution. | Track ecosystem liquidity and stablecoin risks. |
| **On-chain** | Active addresses, transactions, fees, gas, TVL, revenue, bridge flows, staking ratios. | Evaluate network/protocol adoption. |
| **Tokenomics** | Unlock schedules, emissions, burns, treasury, holder concentration, governance proposals. | Evaluate token supply/demand and centralization. |
| **Exchange risk** | Withdrawal status, proof-of-reserves, incident history, regulatory warnings, custody models. | Assess risks of using specific platforms. |
| **Data quality** | Source count, timestamp freshness, cross-source deviation, outlier flags. | Prevents the Agent from answering based on bad data. |

### 14.1. Suggested Alert Thresholds

| Situation | Suggested Threshold | Warning Message |
|---|---|---|
| **Spread widening** | Spread > 0.5%-1% for majors, >2%-3% for small caps. | Thin liquidity; market orders may suffer severe slippage. |
| **Extreme funding** | Funding exceeds 90th/95th percentile of 30-90 day history. | Positions may be crowded; risk of squeeze/liquidation. |
| **Rapid OI spike** | OI +20%-50% in 24h during heavy price volatility. | Leverage is building up rapidly; check liquidation levels. |
| **Stablecoin depeg** | Deviation >0.5% or severely imbalanced DEX pools. | Do not treat this stablecoin as cash; verify reserves/news. |
| **Volume concentration** | >70%-80% volume/depth on one exchange. | Venue concentration risk; price could collapse if exchange halts. |
| **Stale data** | Timestamp exceeds data SLA limits. | Cannot provide real-time analysis; data needs updating. |

## 15. AI Agent Response Playbook
* **"What is a crypto asset?"** -> "A crypto asset is a digital asset relying on cryptography and blockchain/DLT. It can be a native coin, smart contract token, stablecoin, or NFT. When analyzing fundamentals, don't just look at price; evaluate use case, adoption, tokenomics, security, holder rights, liquidity, and regulatory risks."
* **"Which exchange is safe?"** -> "No exchange is entirely risk-free. Look at licenses, custody mechanisms, proof-of-reserves (with liabilities), hack history, real liquidity, fees, withdrawal limits, and Terms of Service. For long-term storage, consider self-custody or professional custodians."
* **"What does positive funding rate mean?"** -> "It usually means longs are paying shorts to hold perpetual positions, often because perp prices are higher than spot or long demand is high. However, positive funding is not an automatic sell signal. Check if it's extreme, if OI is rising, and where liquidations are clustered."
* **"Does this token have good liquidity?"** -> "Don't just look at 24h volume. Check the bid-ask spread, ±1% depth, simulated slippage for your order size, and how many exchanges support it. If liquidity is concentrated on one exchange, exit risks are much higher."
* **"Which stablecoin should I use?"** -> "It depends on your goal (CEX trading, DeFi, storage). Evaluate the peg stability, reserve backing, redemption rights, transparency, liquidity on your specific exchange, and history of depegs. Stablecoins are not risk-free."
* **"Price on Exchange A is different from B, is this arbitrage?"** -> "It might be arbitrage, but it may not be executable. Check trading fees, withdrawal/deposit fees, network congestion, withdrawal halts, KYC limits, actual depth, and stablecoin quote risks. Discrepancies often reflect underlying friction or risk."

## 16. Answer Quality Control Checklist
* **Correct product?** Did the Agent distinguish spot, margin, perps, futures, options?
* **Correct asset?** Did the Agent verify the chain, contract address, ticker, and trading pair?
* **Correct data source?** Where is the price/volume/funding coming from, and is it fresh?
* **Includes risk warnings?** Did the Agent mention custody, liquidity, leverage, stablecoin, or smart contract risks?
* **No definitive recommendations?** Did the Agent avoid "guaranteed to rise", "buy now", or "absolutely safe"?
* **Explains limitations?** Did the Agent state that crypto data can be fragmented, delayed, or manipulated?
* **Dashboard actionable?** Did the Agent suggest specific metrics for the user to observe in the UI?

### 16.1. Escalation Rules
* If asked about legal/tax advice: Provide generic concepts and advise consulting a local professional.
* If asked how to use max leverage: Explain liquidation risks heavily before describing the mechanics.
* If asked to input seeds/private keys/API keys: Refuse, block the input, and guide on security.
* If dashboard data is stale/missing: State clearly that real-time conclusions cannot be drawn.
* If there are signs of a scam/phishing/rug pull: Switch to safety warning mode rather than analyzing profitability.

## 17. Glossary of Terms
* **AMM:** Automated Market Maker, DEX mechanism using liquidity pools and pricing formulas instead of order books.
* **APY/APR:** Annual yields; APR does not compound, APY does. Always verify the source of the yield.
* **Basis:** Difference between derivatives price and spot/index price.
* **Bridge:** Mechanism moving assets/data between blockchains; high-risk vectors.
* **CEX:** Centralized Exchange operated by a company.
* **Cold wallet:** Offline private key storage.
* **DEX:** Decentralized Exchange using smart contracts/AMMs.
* **FDV:** Fully Diluted Valuation (Token price x Max supply).
* **Funding rate:** Periodic payments between longs and shorts in perpetual futures.
* **Gas fee:** Fees paid to blockchain networks to process transactions.
* **Governance token:** Token granting voting rights; does not automatically grant cash flows.
* **Hot wallet:** Internet-connected wallet; convenient but higher hack risk.
* **Index price:** Aggregate reference price from multiple sources.
* **Liquidation:** Forced closure of a position when margin is insufficient.
* **Liquidity pool:** Pool of assets in DeFi providing liquidity for swaps/lending.
* **Market cap:** Price x Circulating supply.
* **MEV:** Maximal Extractable Value; profits bots/validators make by reordering transactions.
* **MPC:** Multi-Party Computation; splitting keys for institutional custody.
* **Oracle:** Data feed bringing off-chain information (like prices) to smart contracts.
* **Perpetual futures:** Derivative contracts with no expiration, using funding rates to peg to spot.
* **Private key:** Cryptographic secret to control blockchain assets.
* **Proof of reserves:** Mechanism proving partial reserves; not a full audit unless liabilities are included.
* **Seed phrase:** Wallet recovery phrase; keep absolutely secret.
* **Slippage:** Difference between expected price and actual execution price.
* **Smart contract:** Self-executing code on a blockchain.
* **Stablecoin:** Crypto asset designed to peg to a reference asset like USD.
* **TVL:** Total Value Locked in a protocol.
* **Wallet:** Tool to interact with keys/accounts; it does not physically store coins.

## 18. Main References
* **Nakamoto, S. (2008)** - Bitcoin: A Peer-to-Peer Electronic Cash System
* **NIST (2018)** - NISTIR 8202: Blockchain Technology Overview
* **Narayanan et al.** - Bitcoin and Cryptocurrency Technologies
* **MIT OpenCourseWare** - Blockchain and Money
* **Antonopoulos & Harding** - Mastering Bitcoin
* **Ethereum.org** - Ethereum accounts and wallets
* **CFA Institute (2023)** - Valuation of Cryptoassets
* **FSB (2022/2023)** - Risk Assessments and Policy Recommendations for Crypto-assets and Stablecoins
* **SEC/CFTC** - Investor Alerts on Crypto Asset Securities and Virtual Currency Trading
* **BIS (2023)** - Financial Stability Risks from Cryptoassets
* **He, Manela, Ross & von Wachter (2022)** - Fundamentals of Perpetual Futures
* **CME Group** - 24/7 Crypto Futures and Options Trading

*(RAG rules: Chunk by headings. Prioritize official sources like NIST, FSB, SEC, CFTC, CFA, Ethereum.org for definitions. Keep regulatory and stablecoin data updated frequently.)*