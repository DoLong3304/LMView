# Deployment Plan - Production Startup

## Objective
Start docker-compose infrastructure without monitoring/logging, ensure OKX + Binance data flows correctly through Bronze → Silver → Gold layers.

## Current Architecture Analysis

### Data Flow
```
OKX/Binance WebSocket → Kafka → Flink → KeyDB + InfluxDB (Hot)
                                      ↓
                                   Bronze (Iceberg/MinIO)
                                      ↓
                                   Silver (Unified)
                                      ↓
                                   Gold (Metrics)
                                      ↓
                                   FastAPI → Frontend
```

### Key Components
1. **Producer** (`src/producer/main.py`) - Dual exchange support (OKX + Binance)
2. **Kafka HA** - 3-node cluster (kafka-1, kafka-2, kafka-3)
3. **Flink** - Stream processing (JobManager + TaskManager)
4. **KeyDB/Redis Sentinel** - Hot cache (1 master + 2 replicas + 3 sentinels)
5. **InfluxDB** - Time-series storage
6. **Spark** - Batch processing (Bronze → Silver → Gold)
7. **MinIO** - S3-compatible storage for Iceberg
8. **Trino** - Federated query engine
9. **Dagster** - Orchestration
10. **FastAPI** - API server
11. **Nginx** - Reverse proxy + frontend

## Codebase Cleanup Analysis

### Files to Merge/Consolidate

#### 1. Orchestration Files (MERGE RECOMMENDED)
**Current:**
- `orchestration/assets.py` (281 lines) - Old Dagster assets
- `orchestration/medallion_assets.py` (388 lines) - New medallion assets

**Issue:** Duplicate asset definitions, both define similar jobs

**Action:** Merge into single `orchestration/assets.py`
- Keep medallion architecture from `medallion_assets.py`
- Add advanced gold metrics assets
- Remove old `assets.py`

#### 2. Batch Jobs (CONSOLIDATE)
**Current:**
- `src/batch/silver_to_gold.py` (199 lines) - Basic gold aggregation
- `src/batch/calculate_all_metrics.py` (NEW) - Comprehensive gold metrics
- `src/batch/market_metrics_calculator.py` (278 lines) - Market metrics (OLD)

**Issue:** Overlapping functionality

**Action:** 
- Keep `calculate_all_metrics.py` as main orchestrator
- Remove `market_metrics_calculator.py` (superseded by `lakehouse/gold/market_metrics.py`)
- Keep `silver_to_gold.py` for coin_ticker table (used by existing API)

#### 3. News Scrapers (CONSOLIDATE)
**Current:**
- `src/news/scraper.py` - Basic scraper
- `src/news/multi_source_scraper.py` - Multi-source
- `src/news/enhanced_scraper.py` - Enhanced version

**Issue:** 3 similar implementations

**Action:** Keep only `enhanced_scraper.py` (most complete), remove others

#### 4. Gold Aggregations (VERIFY USAGE)
**Current:**
- `src/lakehouse/gold/aggregations.py` - Old gold classes (GoldMarketOverview, GoldSymbolStatistics)
- `src/lakehouse/gold/market_metrics.py` - NEW advanced metrics
- `src/lakehouse/gold/news_aggregations.py` - NEW news metrics

**Action:** 
- Keep all (different purposes)
- Update `silver_to_gold.py` to use new classes
- Document which file handles what

## Deployment Steps

### Phase 1: Codebase Cleanup (15 min)

1. **Merge orchestration files**
2. **Remove duplicate batch jobs**
3. **Consolidate news scrapers**
4. **Update imports**

### Phase 2: Infrastructure Startup (10 min)

1. **Start core services** (no monitoring/logging):
   ```bash
   docker-compose up -d zookeeper kafka-1 kafka-2 kafka-3 schema-registry
   docker-compose up -d redis-master redis-replica-1 redis-replica-2
   docker-compose up -d redis-sentinel-1 redis-sentinel-2 redis-sentinel-3
   docker-compose up -d minio postgres influxdb
   ```

2. **Wait for health checks** (2 min)

3. **Start processing layer**:
   ```bash
   docker-compose up -d producer
   docker-compose up -d flink-jobmanager flink-taskmanager
   docker-compose up -d spark-master spark-worker
   docker-compose up -d trino
   ```

4. **Start orchestration**:
   ```bash
   docker-compose up -d dagster-webserver dagster-daemon
   ```

5. **Start serving layer**:
   ```bash
   docker-compose up -d fastapi-dev nginx-dev
   ```

### Phase 3: Verification (15 min)

1. **Check producer logs** - Verify OKX + Binance connections
2. **Check Kafka topics** - Verify data ingestion
3. **Check Flink job** - Verify stream processing
4. **Check KeyDB** - Verify hot cache
5. **Check MinIO** - Verify Bronze data
6. **Run Spark job** - Verify Silver/Gold layers
7. **Test API** - Verify data availability

## Services to EXCLUDE (Monitoring/Logging)

```yaml
# DO NOT START:
- prometheus
- grafana
- loki
- promtail
- node-exporter
- redis-exporter
```

## Expected Data Flow

### Bronze Layer
```sql
-- Should have data from both exchanges
SELECT exchange, COUNT(*) 
FROM iceberg_catalog.bronze.ticker 
WHERE _partition_date = CURRENT_DATE 
GROUP BY exchange;

-- Expected: binance, okx
```

### Silver Layer
```sql
-- Should have unified data
SELECT symbol, price_binance, price_okx, price_mid
FROM iceberg_catalog.silver.ticker_unified
WHERE _partition_date = CURRENT_DATE
LIMIT 10;
```

### Gold Layer
```sql
-- Should have metrics
SELECT * FROM iceberg_catalog.gold.market_dominance
ORDER BY snapshot_time DESC LIMIT 1;

SELECT * FROM iceberg_catalog.gold.movers_ranking
WHERE timeframe = '24h' AND category = 'gainer'
ORDER BY rank LIMIT 10;
```

## Verification Commands

```bash
# 1. Producer status
docker logs producer -f --tail 50

# 2. Kafka topics
docker exec kafka-1 kafka-topics --list --bootstrap-server localhost:9092

# 3. Kafka consumer test
docker exec kafka-1 kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic crypto_ticker \
  --max-messages 5

# 4. KeyDB data
docker exec redis-master redis-cli KEYS "ticker:*" | head -10

# 5. Flink job status
curl http://localhost:8081/jobs

# 6. MinIO buckets
docker exec minio mc ls local/

# 7. Trino query
docker exec trino trino --execute "SHOW TABLES IN iceberg_catalog.bronze"

# 8. API health
curl http://localhost:8000/api/health

# 9. Market overview
curl http://localhost:8000/api/market/overview
```

## Rollback Plan

If issues occur:
```bash
# Stop all
docker-compose down

# Clean volumes (if needed)
docker volume prune -f

# Restart from Phase 2
```

## Success Criteria

✅ Producer connected to OKX + Binance
✅ Kafka receiving messages from both exchanges
✅ Flink processing streams
✅ KeyDB has ticker data with exchange tags
✅ Bronze tables have data from both exchanges
✅ Silver tables have unified data
✅ Gold tables have calculated metrics
✅ API returns market overview
✅ Frontend displays data

## Timeline

- **Cleanup:** 15 min
- **Startup:** 10 min
- **Verification:** 15 min
- **Total:** ~40 min

## Next Steps After Verification

1. Monitor for 1 hour
2. Check data quality
3. Verify exchange source tags
4. Test failover scenarios
5. Document any issues
6. Enable monitoring (optional)
