# LAKEHOUSE TABLES - Complete Schema Reference

> **Purpose:** Complete reference for all Iceberg tables in Medallion Architecture  
> **Storage:** MinIO (S3-compatible)  
> **Format:** Parquet with Snappy compression  
> **Last updated:** 2026-05-11

---

## 📊 Table of Contents

1. [Bronze Layer (Raw Data)](#bronze-layer)
2. [Silver Layer (Cleaned Data)](#silver-layer)
3. [Gold Layer (Business Metrics)](#gold-layer)
4. [Table Statistics](#table-statistics)
5. [Query Examples](#query-examples)

---

## 🥉 Bronze Layer (Raw Data)

**Purpose:** Store raw data from all sources without transformation  
**Retention:** Unlimited (cold storage)  
**Partitioning:** By date and source/exchange

### bronze.ticker

**Description:** Raw ticker data from Binance + OKX

```sql
CREATE TABLE iceberg_catalog.bronze.ticker (
    event_time BIGINT COMMENT 'Unix timestamp in milliseconds',
    symbol STRING COMMENT 'Trading pair (e.g., BTCUSDT)',
    exchange STRING COMMENT 'Exchange name (binance, okx)',
    price DOUBLE COMMENT 'Current price',
    volume DOUBLE COMMENT 'Volume',
    quote_volume DOUBLE COMMENT 'Quote volume',
    change_24h DOUBLE COMMENT '24h price change',
    high_24h DOUBLE COMMENT '24h high price',
    low_24h DOUBLE COMMENT '24h low price',
    raw_payload STRING COMMENT 'Original JSON payload',
    ingestion_time TIMESTAMP COMMENT 'When data was ingested',
    source_system STRING COMMENT 'Source system (flink_streaming)',
    _partition_date DATE COMMENT 'Partition key'
) USING iceberg
PARTITIONED BY (_partition_date, exchange)
TBLPROPERTIES (
    'write.format.default' = 'parquet',
    'write.parquet.compression-codec' = 'snappy'
);
```

**Sample Data:**
```
event_time: 1715443200000
symbol: BTCUSDT
exchange: binance
price: 81234.56
volume: 123.45
_partition_date: 2026-05-11
```

### bronze.kline

**Description:** Raw kline (candlestick) data from all exchanges

```sql
CREATE TABLE iceberg_catalog.bronze.kline (
    event_time BIGINT COMMENT 'Candle open time (ms)',
    symbol STRING COMMENT 'Trading pair',
    exchange STRING COMMENT 'Exchange name',
    `interval` STRING COMMENT 'Timeframe (1m, 5m, 15m, 1h, 4h, 1d, 1w)',
    open_price DOUBLE COMMENT 'Open price',
    high_price DOUBLE COMMENT 'High price',
    low_price DOUBLE COMMENT 'Low price',
    close_price DOUBLE COMMENT 'Close price',
    volume DOUBLE COMMENT 'Volume',
    quote_volume DOUBLE COMMENT 'Quote volume',
    trade_count BIGINT COMMENT 'Number of trades',
    is_closed BOOLEAN COMMENT 'Is candle closed',
    raw_payload STRING COMMENT 'Original JSON',
    ingestion_time TIMESTAMP COMMENT 'Ingestion timestamp',
    source_system STRING COMMENT 'Source system',
    _partition_date DATE COMMENT 'Partition key'
) USING iceberg
PARTITIONED BY (_partition_date, exchange, `interval`)
TBLPROPERTIES (
    'write.format.default' = 'parquet',
    'write.parquet.compression-codec' = 'snappy'
);
```

### bronze.news

**Description:** Raw news articles from 12 sources

```sql
CREATE TABLE iceberg_catalog.bronze.news (
    event_time BIGINT COMMENT 'Published timestamp (ms)',
    source STRING COMMENT 'News source (CoinDesk, CoinTelegraph, etc.)',
    title STRING COMMENT 'Article title',
    content STRING COMMENT 'Full article content',
    url STRING COMMENT 'Article URL',
    author STRING COMMENT 'Article author',
    symbols ARRAY<STRING> COMMENT 'Related symbols (BTC, ETH, etc.)',
    sentiment_score DOUBLE COMMENT 'Sentiment score (-1.0 to 1.0)',
    raw_payload STRING COMMENT 'Original JSON',
    ingestion_time TIMESTAMP COMMENT 'Ingestion timestamp',
    source_system STRING COMMENT 'Source system (dagster_batch)',
    _partition_date DATE COMMENT 'Partition key'
) USING iceberg
PARTITIONED BY (_partition_date, source)
TBLPROPERTIES (
    'write.format.default' = 'parquet',
    'write.parquet.compression-codec' = 'snappy'
);
```

---

## 🥈 Silver Layer (Cleaned Data)

**Purpose:** Deduplicated, validated, unified data  
**Retention:** 90 days  
**Partitioning:** By date and interval

### silver.ticker_unified

**Description:** Unified ticker with mid-price from all exchanges

```sql
CREATE TABLE iceberg_catalog.silver.ticker_unified (
    event_time BIGINT COMMENT 'Unix timestamp (ms)',
    symbol STRING COMMENT 'Trading pair',
    price_binance DOUBLE COMMENT 'Price from Binance',
    price_okx DOUBLE COMMENT 'Price from OKX',
    price_mid DOUBLE COMMENT 'Mid-price: (binance + okx) / 2',
    volume_binance DOUBLE COMMENT 'Volume from Binance',
    volume_okx DOUBLE COMMENT 'Volume from OKX',
    volume_total DOUBLE COMMENT 'Total volume',
    spread_pct DOUBLE COMMENT 'Spread %: |binance - okx| / mid * 100',
    quality_score INT COMMENT 'Data quality (0-100)',
    last_updated TIMESTAMP COMMENT 'Last update time',
    _partition_date DATE COMMENT 'Partition key'
) USING iceberg
PARTITIONED BY (_partition_date)
TBLPROPERTIES (
    'write.format.default' = 'parquet',
    'write.parquet.compression-codec' = 'snappy'
);
```

**Quality Score:**
- 100: Both exchanges have data
- 50: One exchange has data
- 0: No data

### silver.kline_multi_timeframe

**Description:** Multi-timeframe candles (1m to 1w)

```sql
CREATE TABLE iceberg_catalog.silver.kline_multi_timeframe (
    event_time BIGINT COMMENT 'Candle open time (ms)',
    symbol STRING COMMENT 'Trading pair',
    `interval` STRING COMMENT 'Timeframe (1m, 5m, 15m, 1h, 4h, 1d, 1w)',
    open_price DOUBLE COMMENT 'Open price',
    high_price DOUBLE COMMENT 'High price',
    low_price DOUBLE COMMENT 'Low price',
    close_price DOUBLE COMMENT 'Close price',
    volume DOUBLE COMMENT 'Volume',
    trade_count BIGINT COMMENT 'Number of trades',
    is_closed BOOLEAN COMMENT 'Is candle closed',
    quality_score INT COMMENT 'Data quality (0-100)',
    last_updated TIMESTAMP COMMENT 'Last update time',
    _partition_date DATE COMMENT 'Partition key'
) USING iceberg
PARTITIONED BY (_partition_date, `interval`)
TBLPROPERTIES (
    'write.format.default' = 'parquet',
    'write.parquet.compression-codec' = 'snappy'
);
```

**Aggregation Chain:**
```
1m → 5m (5x) → 15m (3x) → 1h (4x) → 4h (4x) → 1d (6x) → 1w (7x)
```

---

## 🥇 Gold Layer (Business Metrics)

**Purpose:** Pre-aggregated business metrics for analytics  
**Retention:** 365 days  
**Partitioning:** By date

### gold.market_overview

**Description:** Market overview with top gainers/losers

```sql
CREATE TABLE iceberg_catalog.gold.market_overview (
    snapshot_time TIMESTAMP COMMENT 'Snapshot timestamp',
    total_symbols INT COMMENT 'Total number of symbols',
    total_volume_24h DOUBLE COMMENT 'Total 24h volume',
    avg_spread_pct DOUBLE COMMENT 'Average spread %',
    top_10_gainers ARRAY<STRUCT<
        symbol:STRING,
        change_pct:DOUBLE,
        price:DOUBLE
    >> COMMENT 'Top 10 gainers',
    top_10_losers ARRAY<STRUCT<
        symbol:STRING,
        change_pct:DOUBLE,
        price:DOUBLE
    >> COMMENT 'Top 10 losers',
    market_cap_total DOUBLE COMMENT 'Total market cap',
    _partition_date DATE COMMENT 'Partition key'
) USING iceberg
PARTITIONED BY (_partition_date)
TBLPROPERTIES (
    'write.format.default' = 'parquet',
    'write.parquet.compression-codec' = 'snappy'
);
```

### gold.symbol_stats_daily

**Description:** Daily statistics per symbol

```sql
CREATE TABLE iceberg_catalog.gold.symbol_stats_daily (
    symbol STRING COMMENT 'Trading pair',
    date DATE COMMENT 'Date',
    open_price DOUBLE COMMENT 'Open price',
    high_price DOUBLE COMMENT 'High price',
    low_price DOUBLE COMMENT 'Low price',
    close_price DOUBLE COMMENT 'Close price',
    volume_24h DOUBLE COMMENT '24h volume',
    change_pct_24h DOUBLE COMMENT '24h change %',
    volatility DOUBLE COMMENT 'Price volatility (stddev)',
    avg_spread_pct DOUBLE COMMENT 'Average spread %',
    trade_count BIGINT COMMENT 'Number of trades',
    price_range_pct DOUBLE COMMENT 'Price range %: (high - low) / low * 100'
) USING iceberg
PARTITIONED BY (date)
TBLPROPERTIES (
    'write.format.default' = 'parquet',
    'write.parquet.compression-codec' = 'snappy'
);
```

### gold.sector_performance

**Description:** Sector-level performance metrics

```sql
CREATE TABLE iceberg_catalog.gold.sector_performance (
    sector STRING COMMENT 'Sector (Large Cap, Mid Cap, Small Cap)',
    snapshot_time TIMESTAMP COMMENT 'Snapshot timestamp',
    avg_change_pct DOUBLE COMMENT 'Average change %',
    total_volume DOUBLE COMMENT 'Total volume',
    symbol_count INT COMMENT 'Number of symbols',
    top_symbol STRING COMMENT 'Top performing symbol',
    top_symbol_change_pct DOUBLE COMMENT 'Top symbol change %',
    _partition_date DATE COMMENT 'Partition key'
) USING iceberg
PARTITIONED BY (_partition_date)
TBLPROPERTIES (
    'write.format.default' = 'parquet',
    'write.parquet.compression-codec' = 'snappy'
);
```

**Sector Classification:**
- Large Cap: volume_24h > 1,000,000
- Mid Cap: volume_24h > 100,000
- Small Cap: volume_24h <= 100,000

### gold.market_metrics_realtime

**Description:** Real-time market metrics (updated every 5 min)

```sql
CREATE TABLE iceberg_catalog.gold.market_metrics_realtime (
    symbol STRING COMMENT 'Trading pair',
    current_price DOUBLE COMMENT 'Current price',
    price_1h_ago DOUBLE COMMENT 'Price 1 hour ago',
    price_24h_ago DOUBLE COMMENT 'Price 24 hours ago',
    price_7d_ago DOUBLE COMMENT 'Price 7 days ago',
    change_1h_pct DOUBLE COMMENT '1h change %',
    change_24h_pct DOUBLE COMMENT '24h change %',
    change_7d_pct DOUBLE COMMENT '7d change %',
    volume_24h DOUBLE COMMENT '24h volume',
    high_24h DOUBLE COMMENT '24h high',
    low_24h DOUBLE COMMENT '24h low',
    market_cap DOUBLE COMMENT 'Market cap (price * volume)',
    rank INT COMMENT 'Rank by market cap',
    last_updated TIMESTAMP COMMENT 'Last update time'
) USING iceberg
TBLPROPERTIES (
    'write.format.default' = 'parquet',
    'write.parquet.compression-codec' = 'snappy',
    'write.distribution-mode' = 'hash'
);
```

---

## 📊 Table Statistics

### Storage Estimates (per day)

| Table | Records/Day | Size/Day | Retention | Total Size |
|-------|-------------|----------|-----------|------------|
| **bronze.ticker** | ~10M | ~500MB | Unlimited | Growing |
| **bronze.kline** | ~2M | ~200MB | Unlimited | Growing |
| **bronze.news** | ~2K | ~10MB | Unlimited | Growing |
| **silver.ticker_unified** | ~5M | ~300MB | 90 days | ~27GB |
| **silver.kline_multi_timeframe** | ~1M | ~100MB | 90 days | ~9GB |
| **gold.market_overview** | ~288 | ~1MB | 365 days | ~365MB |
| **gold.symbol_stats_daily** | ~150 | ~1MB | 365 days | ~365MB |
| **gold.sector_performance** | ~288 | ~1MB | 365 days | ~365MB |
| **gold.market_metrics_realtime** | ~150 | ~1MB | 7 days | ~7MB |

**Total Storage (90 days):** ~40GB

### Partition Strategy

**Bronze Layer:**
- Partition by: `_partition_date`, `exchange`/`source`
- Reason: Efficient filtering by date and source

**Silver Layer:**
- Partition by: `_partition_date`, `interval` (for klines)
- Reason: Efficient timeframe queries

**Gold Layer:**
- Partition by: `_partition_date`
- Reason: Daily aggregations

---

## 🔍 Query Examples

### Bronze Layer Queries

```sql
-- Get raw ticker data for BTC from Binance (last 24h)
SELECT *
FROM iceberg_catalog.bronze.ticker
WHERE symbol = 'BTCUSDT'
  AND exchange = 'binance'
  AND _partition_date >= CURRENT_DATE - INTERVAL '1' DAY
ORDER BY event_time DESC
LIMIT 100;

-- Count news articles by source (last 7 days)
SELECT source, COUNT(*) as article_count
FROM iceberg_catalog.bronze.news
WHERE _partition_date >= CURRENT_DATE - INTERVAL '7' DAY
GROUP BY source
ORDER BY article_count DESC;
```

### Silver Layer Queries

```sql
-- Get unified ticker with spread analysis
SELECT
    symbol,
    price_mid,
    spread_pct,
    quality_score,
    CASE
        WHEN spread_pct > 1.0 THEN 'High Spread'
        WHEN spread_pct > 0.5 THEN 'Medium Spread'
        ELSE 'Low Spread'
    END as spread_category
FROM iceberg_catalog.silver.ticker_unified
WHERE _partition_date = CURRENT_DATE
  AND quality_score = 100
ORDER BY spread_pct DESC
LIMIT 20;

-- Get 1h candles for BTC (last 7 days)
SELECT
    FROM_UNIXTIME(event_time / 1000) as time,
    open_price,
    high_price,
    low_price,
    close_price,
    volume
FROM iceberg_catalog.silver.kline_multi_timeframe
WHERE symbol = 'BTCUSDT'
  AND `interval` = '1h'
  AND _partition_date >= CURRENT_DATE - INTERVAL '7' DAY
ORDER BY event_time;
```

### Gold Layer Queries

```sql
-- Get latest market overview
SELECT
    snapshot_time,
    total_symbols,
    total_volume_24h,
    avg_spread_pct,
    CARDINALITY(top_10_gainers) as gainer_count,
    CARDINALITY(top_10_losers) as loser_count
FROM iceberg_catalog.gold.market_overview
ORDER BY snapshot_time DESC
LIMIT 1;

-- Get top 10 gainers from latest snapshot
SELECT
    gainer.symbol,
    gainer.change_pct,
    gainer.price
FROM iceberg_catalog.gold.market_overview
LATERAL VIEW EXPLODE(top_10_gainers) t AS gainer
ORDER BY snapshot_time DESC
LIMIT 10;

-- Get daily stats for BTC (last 30 days)
SELECT
    date,
    open_price,
    high_price,
    low_price,
    close_price,
    change_pct_24h,
    volatility
FROM iceberg_catalog.gold.symbol_stats_daily
WHERE symbol = 'BTCUSDT'
  AND date >= CURRENT_DATE - INTERVAL '30' DAY
ORDER BY date DESC;

-- Get real-time top gainers (24h)
SELECT
    symbol,
    current_price,
    change_24h_pct,
    volume_24h,
    rank
FROM iceberg_catalog.gold.market_metrics_realtime
WHERE change_24h_pct > 0
ORDER BY change_24h_pct DESC
LIMIT 10;
```

### Cross-Layer Queries

```sql
-- Compare raw vs unified ticker prices
SELECT
    b.symbol,
    b.exchange,
    b.price as raw_price,
    s.price_mid as unified_price,
    ABS(b.price - s.price_mid) as price_diff
FROM iceberg_catalog.bronze.ticker b
JOIN iceberg_catalog.silver.ticker_unified s
  ON b.symbol = s.symbol
  AND b._partition_date = s._partition_date
WHERE b._partition_date = CURRENT_DATE
  AND ABS(b.price - s.price_mid) > 10
ORDER BY price_diff DESC;
```

---

## 🛠️ Maintenance

### Compaction

```sql
-- Compact small files (run daily)
CALL iceberg_catalog.system.rewrite_data_files(
    table => 'iceberg_catalog.bronze.ticker',
    strategy => 'binpack',
    options => map('target-file-size-bytes', '536870912')  -- 512MB
);
```

### Expire Snapshots

```sql
-- Expire old snapshots (run weekly)
CALL iceberg_catalog.system.expire_snapshots(
    table => 'iceberg_catalog.bronze.ticker',
    older_than => TIMESTAMP '2026-04-11 00:00:00',
    retain_last => 10
);
```

### Remove Old Partitions

```sql
-- Remove partitions older than retention period
ALTER TABLE iceberg_catalog.silver.ticker_unified
DROP PARTITION (_partition_date < '2026-02-11');
```

---

## 📈 Performance Tips

1. **Always filter by partition columns** (`_partition_date`, `exchange`, `interval`)
2. **Use predicate pushdown** (filter in WHERE clause, not after JOIN)
3. **Limit result sets** (use LIMIT for exploratory queries)
4. **Use appropriate file sizes** (512MB target for compaction)
5. **Monitor query plans** (use EXPLAIN to check partition pruning)

---

**Last Updated:** 2026-05-11  
**Total Tables:** 9 (3 Bronze + 2 Silver + 4 Gold)  
**Total Storage:** ~40GB (90-day retention)
