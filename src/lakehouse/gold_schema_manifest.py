"""
Gold Layer Schema Manifest — CANONICAL SOURCE OF TRUTH (P1 fix).

## Why this file exists

Prior to v0.24.4, two parallel Gold aggregation systems ran in
parallel and produced different schemas for the SAME business
concept (e.g. BTC dominance):

1. **Trino-based** (src/lakehouse/gold_aggregator_trino.py)
   - Tables: ``gold_movers_ranking``, ``gold_market_dominance``,
     ``gold_volatility_ranking``, ``gold_momentum_indicators``,
     ``gold_sector_performance``, ``gold_news_sentiment_daily``
   - Per-row granularity (one row per symbol/exchange)
   - Source: bronze ``coin_ticker`` / ``coin_klines``
   - Used by: **backend/api/market_overview.py** (the only API consumer)

2. **Spark-based** (src/lakehouse/gold/{market_metrics,aggregations}.py)
   - Tables: ``market_dominance``, ``volatility_ranking``,
     ``movers_ranking``, ``gold_market_overview``,
     ``gold_sector_performance``, ``gold_symbol_stats_daily``
   - Single-row or array-of-structs granularity
   - Source: silver ``silver_ticker_unified`` / ``silver_kline_multi_timeframe``
   - Used by: **no one (orphaned)**

The Drift made the API's behaviour depend entirely on whether the
Trino job had run in the last ``GOLD_FRESHNESS_MINUTES`` (30 min);
otherwise the API silently fell back to ``_derive_market_from_redis``.
Meanwhile the Spark job burned cluster compute producing tables
nothing read.

## P1 fix (v0.24.4): Unify on Trino

- **Canonical schema = Trino-based** (because it's the only one the
  API reads).
- **Spark-based jobs deferred**: code kept, schedules disabled, all
  Spark tables marked ``DEPRECATED`` here.
- **If/when we re-enable Spark**, the schema in this file is the
  target. The mapping functions below translate Spark output into
  the canonical schema.

## Schema columns

Each ``GOLD_TABLE_*`` constant lists the columns the API and any
downstream consumer can rely on. ``_partition_date`` is implicit
(partitioned on it). Column types are SQL-style for documentation
but enforced in Trino DDL at create time.

DO NOT add new fields to these tables without updating this file
AND the API code that reads them.
"""

from __future__ import annotations

# ─────────────────────────────────────────────────────────────────────────────
# Canonical Gold table schemas
# ─────────────────────────────────────────────────────────────────────────────

# gold_movers_ranking
# Per-row: top-100 gainers + top-100 losers (price change ranked 24h).
# API uses this for /overview, /rankings/{gainers,losers,volume}, /heatmap.
GOLD_TABLE_MOVERS_RANKING = {
    "symbol": "VARCHAR",                # e.g. "BTCUSDT"
    "exchange": "VARCHAR",              # e.g. "binance"
    "price": "DOUBLE",                  # last close price
    "change_24h": "DOUBLE",             # pct change over 24h
    "volume_24h": "DOUBLE",             # quote-asset volume over 24h
    "rank_gainers": "INTEGER",          # 1..100 (NULL if loser)
    "rank_losers": "INTEGER",           # 1..100 (NULL if gainer)
    "computed_at": "TIMESTAMP WITH TIME ZONE",
}

# gold_market_dominance
# Per-row: one row per symbol with its share of total volume + summary.
# API uses this for /overview market_summary (BTC/ETH dominance).
GOLD_TABLE_MARKET_DOMINANCE = {
    "symbol": "VARCHAR",
    "exchange": "VARCHAR",
    "volume_24h": "DOUBLE",
    "volume_pct": "DOUBLE",             # share of total volume (0-100)
    "computed_at": "TIMESTAMP WITH TIME ZONE",
    "active_symbols": "INTEGER",        # denormalised; same on every row
    "total_volume_24h": "DOUBLE",       # denormalised; same on every row
    "btc_dominance_pct": "DOUBLE",      # denormalised; same on every row
    "eth_dominance_pct": "DOUBLE",      # denormalised; same on every row
}

# gold_volatility_ranking
# Per-row: top-200 most volatile symbols (60-period kline range).
# API uses this for /overview most_volatile.
GOLD_TABLE_VOLATILITY_RANKING = {
    "symbol": "VARCHAR",
    "exchange": "VARCHAR",
    "price_range_pct": "DOUBLE",        # (max(high)-min(low))/avg(close) * 100
    "atr_estimate": "DOUBLE",           # price_range_pct / 100 (proxy)
    "rank": "INTEGER",                  # 1..200 by price_range_pct DESC
    "computed_at": "TIMESTAMP WITH TIME ZONE",
}

# gold_momentum_indicators
# Per-row: SMA20-based trend direction per symbol.
# API uses this for /overview indicators_summary.
GOLD_TABLE_MOMENTUM_INDICATORS = {
    "symbol": "VARCHAR",
    "exchange": "VARCHAR",
    "rsi_signal": "VARCHAR",            # 'overbought' | 'oversold' | 'neutral' (currently always 'neutral' in Trino; see RAG limitation)
    "trend_direction": "VARCHAR",       # 'up' | 'down' | 'sideways'
    "macd_signal": "VARCHAR",           # 'bullish_cross' | 'bearish_cross' | 'none' (currently always 'none' in Trino)
    "score": "DOUBLE",                  # -1.0..+1.0
    "computed_at": "TIMESTAMP WITH TIME ZONE",
}

# gold_sector_performance
# Per-row: one row per sector (Large/Mid/Small cap tier).
# API uses this for /overview sector_performance.
GOLD_TABLE_SECTOR_PERFORMANCE = {
    "sector": "VARCHAR",                # 'Large Cap' | 'Mid Cap' | 'Small Cap'
    "avg_change_pct": "DOUBLE",         # mean 24h change across symbols in sector
    "total_volume": "DOUBLE",           # sum of 24h quote volume
    "symbol_count": "INTEGER",          # number of symbols in sector
    "computed_at": "TIMESTAMP WITH TIME ZONE",
}

# gold_news_sentiment_daily
# Per-row: per symbol per day, aggregated from news_articles.
# API uses this for /overview trending_news.
GOLD_TABLE_NEWS_SENTIMENT_DAILY = {
    "date": "TIMESTAMP WITH TIME ZONE",
    "symbol": "VARCHAR",
    "avg_sentiment": "DOUBLE",          # -1.0..+1.0
    "article_count": "BIGINT",
    "bullish_count": "BIGINT",
    "bearish_count": "BIGINT",
}

# gold_news_market_impact (v0.24.5 - Task 4)
# Per-row: per news article × symbol, with measured price impact at
# t+1h, t+4h, t+24h after publication. Quantifies "how much did
# BTC move after this ETF approval headline?" — a direct competitive
# response to TradingView News + CryptoQuant Impact features.
#
# Computed by: src/lakehouse/gold/news_impact.py (Spark batch job,
# scheduled hourly). Joins silver_news_enriched with silver_kline_1h
# using windowed lookups.
#
# Notes:
# - Exchange field is the reference price feed (default: binance).
#   All price_*_after and change_*_pct fields are NULLABLE because
#   the underlying kline may not exist (young article, symbol delisted,
#   or low-volume symbol with gaps).
# - impact_score = max(|change_1h|, |change_4h|, |change_24h|) * sign(sentiment).
#   Positive score = bullish news that moved price up.
#   Negative score = bearish news that moved price down.
GOLD_TABLE_NEWS_MARKET_IMPACT = {
    "news_id":           "BIGINT",
    "symbol":            "VARCHAR",
    "exchange":          "VARCHAR",       # price reference (default 'binance')
    "published_at":      "TIMESTAMP WITH TIME ZONE",
    "headline":          "VARCHAR",
    "url":               "VARCHAR",
    "source":            "VARCHAR",
    "sentiment":         "DOUBLE",        # -1.0..+1.0
    "price_at_news":     "DOUBLE",        # close at 1h kline containing published_at
    "price_1h_after":    "DOUBLE",        # NULL if kline missing
    "price_4h_after":    "DOUBLE",
    "price_24h_after":   "DOUBLE",
    "change_1h_pct":     "DOUBLE",        # (price_1h - price_at) / price_at * 100
    "change_4h_pct":     "DOUBLE",
    "change_24h_pct":    "DOUBLE",
    "impact_score":      "DOUBLE",        # see formula above
    "computed_at":       "TIMESTAMP WITH TIME ZONE",
}

# liquidity_heatmap (v0.24.5 - Task 5)
# Per-row: per (symbol, time_bucket, side, price_bucket), with the
# summed resting-order quantity in that bucket during that minute.
# Source: Flink writer src/processing/writers/liquidity_heatmap.py
# consuming crypto_depth. NOT a Trino table — read path is direct
# from InfluxDB via the API. This entry is here for manifest
# completeness (so audit scripts can verify the upstream writer is
# registered) and to document the shape for the API consumer.
#
# Caveat: exchange tag may default to 'binance' even for non-binance
# sources because the upstream depth Kafka topic drops the exchange
# field in some pipeline paths (AGENTS.md known hot-spot). Document
# this in any user-visible UI tooltip.
#
# Bucketing: BUCKET_PCT=0.1 (10 bps) × MAX_BUCKETS=100 → covers
# ±1% around mid-price in 200 total buckets (100 bid + 100 ask).
LIQUIDITY_HEATMAP_SCHEMA = {
    "exchange":      "VARCHAR",       # default 'binance' (see caveat)
    "symbol":        "VARCHAR",
    "side":          "VARCHAR",       # 'bid' | 'ask'
    "price_bucket":  "INTEGER",       # 0 = at mid, 1 = first level away, ...
    "quantity":      "DOUBLE",        # summed resting qty
    "order_count":   "BIGINT",        # number of levels contributing
    "time_bucket":   "BIGINT",        # minute epoch UTC (ms)
}


# ─────────────────────────────────────────────────────────────────────────────
# Table list + metadata
# ─────────────────────────────────────────────────────────────────────────────

CANONICAL_GOLD_TABLES: dict[str, dict[str, str]] = {
    "gold_movers_ranking": GOLD_TABLE_MOVERS_RANKING,
    "gold_market_dominance": GOLD_TABLE_MARKET_DOMINANCE,
    "gold_volatility_ranking": GOLD_TABLE_VOLATILITY_RANKING,
    "gold_momentum_indicators": GOLD_TABLE_MOMENTUM_INDICATORS,
    "gold_sector_performance": GOLD_TABLE_SECTOR_PERFORMANCE,
    "gold_news_sentiment_daily": GOLD_TABLE_NEWS_SENTIMENT_DAILY,
    "gold_news_market_impact": GOLD_TABLE_NEWS_MARKET_IMPACT,
    "liquidity_heatmap": LIQUIDITY_HEATMAP_SCHEMA,
    "whale_alerts": {
        # Read path: Redis sorted set, written by
        # src/processing/writers/whale_alert.py. This entry exists for
        # manifest completeness (so /audit scripts can verify the
        # upstream writer is registered) but is NOT a Trino table —
        # the API reads directly from Redis for hot-path latency.
        "trade_id":     "BIGINT",
        "symbol":       "VARCHAR",
        "exchange":     "VARCHAR",
        "side":         "VARCHAR",        # buy | sell
        "price":        "DOUBLE",
        "quantity":     "DOUBLE",
        "notional_usd": "DOUBLE",
        "trade_time":   "BIGINT",          # ms epoch (also the score in Redis)
        "detected_at":  "BIGINT",          # ms epoch (when Flink saw the trade)
    },
}


# Spark-based tables that are DEPRECATED. Code is kept for reference but
# Dagster schedules no longer run them. They may be re-enabled only after
# their schemas are brought into alignment with the canonical tables above.
DEPRECATED_SPARK_TABLES: dict[str, str] = {
    "market_dominance":
        "Spark single-row dominance. Replaced by gold_market_dominance "
        "(per-row). No API consumer.",
    "volatility_ranking":
        "Spark per-symbol volatility with 1h/24h/7d windows. Replaced by "
        "gold_volatility_ranking (60-period range). No API consumer.",
    "movers_ranking":
        "Spark per-symbol gainers/losers with 1h/24h/7d timeframes. "
        "Replaced by gold_movers_ranking (24h). No API consumer.",
    "gold_market_overview":
        "Spark single-row overview with nested-array top-10. Replaced by "
        "gold_movers_ranking + gold_market_dominance. No API consumer.",
    "gold_sector_performance":
        "Spark sector (Large/Mid/Small cap). Same name as canonical but "
        "different schema (adds top_symbol, top_symbol_change_pct). No "
        "API consumer; canonical version is what /overview uses.",
    "gold_symbol_stats_daily":
        "Spark per-symbol per-day stats. Replaced by computing on the fly "
        "from silver_ticker_unified. No API consumer.",
}


# ─────────────────────────────────────────────────────────────────────────────
# Constants exposed for tests
# ─────────────────────────────────────────────────────────────────────────────

# Freshness window the API accepts before falling back to Redis.
# Matches ``GOLD_FRESHNESS_MINUTES`` in backend/api/market_overview.py.
GOLD_FRESHNESS_MINUTES = 30

# Which Dagster job is the canonical producer of these tables.
# Schedules that write to canonical tables MUST be in this list.
CANONICAL_PRODUCER_JOB = "gold_layer_job"


def list_canonical_tables() -> list[str]:
    """Return the list of canonical Gold table names."""
    return list(CANONICAL_GOLD_TABLES.keys())


def get_table_schema(table_name: str) -> dict[str, str] | None:
    """Return the canonical schema for a Gold table, or None if unknown."""
    return CANONICAL_GOLD_TABLES.get(table_name)


def is_deprecated_spark_table(table_name: str) -> bool:
    """Return True if the table is a deprecated Spark-only table."""
    return table_name in DEPRECATED_SPARK_TABLES
