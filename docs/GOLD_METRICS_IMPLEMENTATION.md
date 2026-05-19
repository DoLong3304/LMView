# Gold Layer Metrics Implementation Summary

## Overview
Comprehensive gold layer metrics system for market overview, rankings, heatmaps, and technical analysis.

## Architecture

### Data Flow
```
Bronze (Raw) → Silver (Cleaned) → Gold (Metrics) → API → Frontend
```

### Components Created

#### 1. News Pipeline
- **Bronze**: `bronze.news` - Raw articles from 12 sources
- **Silver**: `silver.news_enriched` - Deduplicated + quality scored
- **Gold**: `gold.news_sentiment_daily` - Daily sentiment per symbol

**Files**:
- `src/lakehouse/bronze/news_writer.py` - Write raw news to Iceberg
- `src/lakehouse/silver/news_transformer.py` - Transform & enrich
- `src/lakehouse/gold/news_aggregations.py` - Sentiment aggregations

#### 2. Market Metrics
**Gold Tables**:
- `gold.market_dominance` - BTC/ETH dominance, market cap, volume
- `gold.volatility_ranking` - Volatility rankings (1h, 24h, 7d)
- `gold.movers_ranking` - Top gainers/losers with volume context
- `gold.momentum_indicators` - RSI, MACD, Bollinger Bands

**Files**:
- `src/lakehouse/gold/market_metrics.py` - Market dominance, volatility, movers
- `src/batch/calculate_indicators.py` - Technical indicators (RSI, MACD, BB)
- `src/batch/calculate_all_metrics.py` - Orchestration script

#### 3. API Layer
**Endpoints**:
- `GET /api/market/overview` - Comprehensive market overview
  - Market summary (cap, volume, dominance)
  - Top gainers/losers
  - Most volatile
  - Highest volume
  - Trending news
  - Sector performance
  - Heatmap data
  - Technical indicators summary

- `GET /api/market/heatmap` - Heatmap visualization data
- `GET /api/market/rankings/{category}` - Rankings by category

**Files**:
- `backend/api/market_overview.py` - Overview API endpoints
- `backend/services/heatmap_service.py` - Heatmap data generation

#### 4. Orchestration
**Dagster Assets**:
- `calculate_gold_metrics` - Run all gold metrics
- `calculate_indicators` - Run technical indicators
- Schedule: Every 5 minutes

**Files**:
- `orchestration/medallion_assets.py` - Updated with new assets

## Database Schema

### News Tables

```sql
-- Bronze: Raw news
CREATE TABLE bronze.news (
    id STRING,
    event_time BIGINT,
    source STRING,
    title STRING,
    summary STRING,
    content STRING,
    url STRING,
    symbols ARRAY<STRING>,
    sentiment_score DOUBLE,
    sentiment_label STRING,
    _partition_date DATE
) PARTITIONED BY (_partition_date, source);

-- Silver: Enriched news
CREATE TABLE silver.news_enriched (
    id STRING,
    published_at BIGINT,
    source STRING,
    title STRING,
    summary STRING,
    url STRING,
    symbols ARRAY<STRING>,
    sentiment_score DOUBLE,
    impact_score DOUBLE,
    quality_score INT,
    _partition_date DATE
) PARTITIONED BY (_partition_date);

-- Gold: Daily sentiment
CREATE TABLE gold.news_sentiment_daily (
    symbol STRING,
    date DATE,
    article_count INT,
    avg_sentiment DOUBLE,
    sentiment_positive INT,
    sentiment_neutral INT,
    sentiment_negative INT,
    top_headlines ARRAY<STRUCT<...>>
) PARTITIONED BY (date);
```

### Market Metrics Tables

```sql
-- Market dominance
CREATE TABLE gold.market_dominance (
    snapshot_time TIMESTAMP,
    btc_dominance_pct DOUBLE,
    eth_dominance_pct DOUBLE,
    total_market_cap DOUBLE,
    total_volume_24h DOUBLE,
    active_symbols INT,
    _partition_date DATE
) PARTITIONED BY (_partition_date);

-- Volatility ranking
CREATE TABLE gold.volatility_ranking (
    symbol STRING,
    volatility_1h DOUBLE,
    volatility_24h DOUBLE,
    volatility_7d DOUBLE,
    rank_by_volatility INT,
    price_range_pct_24h DOUBLE,
    _partition_date DATE
) PARTITIONED BY (_partition_date);

-- Movers ranking
CREATE TABLE gold.movers_ranking (
    symbol STRING,
    rank INT,
    category STRING,  -- 'gainer' or 'loser'
    timeframe STRING,  -- '1h', '24h', '7d'
    change_pct DOUBLE,
    current_price DOUBLE,
    volume_24h DOUBLE,
    volume_change_pct DOUBLE,
    _partition_date DATE
) PARTITIONED BY (_partition_date, timeframe);

-- Technical indicators
CREATE TABLE gold.momentum_indicators (
    symbol STRING,
    rsi_14 DOUBLE,
    macd DOUBLE,
    macd_signal DOUBLE,
    macd_histogram DOUBLE,
    bb_upper DOUBLE,
    bb_middle DOUBLE,
    bb_lower DOUBLE,
    price_sma_20 DOUBLE,
    price_sma_50 DOUBLE,
    price_ema_12 DOUBLE,
    price_ema_26 DOUBLE,
    _partition_date DATE
) PARTITIONED BY (_partition_date);
```

## API Response Example

```json
{
  "timestamp": "2026-05-17T10:30:00Z",
  "timeframe": "24h",
  "market_summary": {
    "total_market_cap": 2500000000000,
    "total_volume_24h": 120000000000,
    "btc_dominance": 45.2,
    "eth_dominance": 18.3,
    "active_symbols": 150,
    "fear_greed_index": 65
  },
  "top_gainers": [
    {
      "symbol": "BTCUSDT",
      "rank": 1,
      "change_pct": 5.2,
      "price": 81234.56,
      "volume_24h": 1200000000,
      "volume_change_pct": 15.3
    }
  ],
  "top_losers": [...],
  "most_volatile": [...],
  "highest_volume": [...],
  "trending_news": [
    {
      "symbol": "BTC",
      "article_count": 45,
      "avg_sentiment": 0.7,
      "sentiment_positive": 35,
      "sentiment_negative": 5
    }
  ],
  "sector_performance": {
    "large_cap": {"change_pct": 2.1, "volume": 50000000000},
    "mid_cap": {"change_pct": -1.2, "volume": 20000000000},
    "small_cap": {"change_pct": 3.5, "volume": 5000000000}
  },
  "heatmap_data": [...],
  "indicators_summary": {
    "total_symbols": 150,
    "avg_rsi": 52.3,
    "overbought_count": 12,
    "oversold_count": 8,
    "bullish_macd_count": 85,
    "bearish_macd_count": 65
  }
}
```

## Realtime Data Flow

### Current Status
- **Producer**: Configured for OKX + Binance websockets ✓
- **Pipeline**: WebSocket → Kafka → Flink → KeyDB → API ✓
- **Containers**: Currently stopped (need restart)

### Verification Steps
1. Start containers: `docker-compose up -d`
2. Check producer logs: `docker logs producer -f`
3. Verify Kafka topics: `docker exec kafka-1 kafka-topics --list`
4. Check KeyDB data: `docker exec redis-master redis-cli KEYS "ticker:*"`
5. Test API: `curl http://localhost:8000/api/market/overview`

## Next Steps

1. **Start Infrastructure**:
   ```bash
   docker-compose up -d
   ```

2. **Run Initial Metrics Calculation**:
   ```bash
   docker exec spark-master spark-submit /app/src/batch/calculate_all_metrics.py
   docker exec spark-master spark-submit /app/src/batch/calculate_indicators.py
   ```

3. **Verify API**:
   ```bash
   curl http://localhost:8000/api/market/overview
   curl http://localhost:8000/api/market/heatmap
   curl http://localhost:8000/api/market/rankings/gainers
   ```

4. **Frontend Integration**:
   - Connect Overview tab to `/api/market/overview`
   - Implement heatmap visualization with `/api/market/heatmap`
   - Add rankings tables with `/api/market/rankings/{category}`

## Files Created

1. `src/lakehouse/bronze/news_writer.py`
2. `src/lakehouse/silver/news_transformer.py`
3. `src/lakehouse/gold/news_aggregations.py`
4. `src/lakehouse/gold/market_metrics.py`
5. `src/batch/calculate_indicators.py`
6. `src/batch/calculate_all_metrics.py`
7. `backend/api/market_overview.py`
8. `backend/services/heatmap_service.py`
9. `orchestration/medallion_assets.py` (updated)
10. `backend/app.py` (updated)

## Performance Considerations

- **Partitioning**: All tables partitioned by date for efficient queries
- **Caching**: API responses can be cached (5-minute TTL)
- **Batch Size**: Metrics calculated every 5 minutes
- **Indicators**: Use 7-day window for sufficient history
- **Heatmap**: Limit to top 50-100 symbols for performance

## Monitoring

- **Dagster UI**: Monitor job execution
- **Spark UI**: Monitor Spark job performance
- **Grafana**: Add dashboards for gold metrics
- **API Logs**: Monitor API response times
