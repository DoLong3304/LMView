# Lakehouse Layer — Spark + Iceberg + MinIO + Trino

Batch/analytical path for long-term historical data.

## Architecture

```
Kafka → Spark Structured Streaming → Iceberg (Bronze→Silver→Gold) → MinIO → Trino SQL
```

## Components

### Apache Spark 3.5.5

- **spark-master**: Cluster coordinator (1 replica, on worker node)
- **spark-worker**: Executor (2 replicas, on worker node)
- **spark-submit**: Submits streaming job and keeps it running (0/1 replicas currently — manual submit)

Memory: 2GB per executor. Image: `cryptoprice/spark:3.5.5` (custom, Hadoop + AWS SDK included).

### src/lakehouse/pipeline.py

Spark Structured Streaming job:
1. Reads Kafka (Confluent Avro format, strips 5-byte header)
2. `from_avro()` deserialization
3. Writes to Iceberg tables in MinIO
4. Catalog: JDBC catalog → PostgreSQL (`iceberg_catalog` database)

### Medallion Architecture

| Layer | Purpose | Tables |
|---|---|---|
| **Bronze** | Raw data, no transformations | `coin_ticker`, `coin_klines`, `coin_trades`, `coin_depth`, `news_articles` |
| **Silver** | Cleaned, validated, exchange-typed | `clean_ticker`, `clean_klines`, `clean_trades`, `clean_news` |
| **Gold** | Aggregated metrics for API | `market_overview`, `top_gainers_losers`, `market_heatmap`, `news_sentiment`, `news_impact` |

### src/lakehouse/bronze/writers.py
- Kafka → Iceberg direct writes
- Type conversion, timestamp normalization
- Exchange field included in DDL

### src/lakehouse/silver/transformations.py
- Dedup, null handling, data type fixes
- Exchange field cleanup
- Schema evolution handling

### src/lakehouse/gold/aggregations.py
- Market overview: 24h performance, volume, dominance
- Gainers/losers: top/bottom 20 by change %
- Heatmap: market cap buckets, performance coloring
- All read by FastAPI via Trino

### MinIO

- S3-compatible object storage
- Ports: 9000 (API), 9001 (Console)
- Buckets: `cryptoprice/iceberg/*`, `flink-checkpoints/`
- MinIO-init: one-shot bucket creation
- Iceberg catalog: JDBC → PostgreSQL

### Trino

- Distributed SQL engine for Iceberg queries
- Port: 8083 (published)
- Catalog: `iceberg_catalog` → PostgreSQL catalog → MinIO Iceberg tables
- Used by FastAPI for: historical klines, market overview, heatmap, rankings

## Batch Jobs (src/batch/)

| Script | Purpose | Schedule |
|---|---|---|
| backfill.py | Historical data import from Binance REST | One-shot |
| aggregate.py | Retention maintenance | Monthly |
| maintenance.py | Iceberg compaction, snapshot expiry, orphan cleanup | Monthly |
| bronze_to_silver.py | Medallion bronze→silver | Hourly |
| silver_to_gold.py | Medallion silver→gold | Hourly |
| calculate_indicators.py | Batch indicator computation | On-demand |
| calculate_all_metrics.py | Full metric recalculation | On-demand |
| unified/ | Consolidated Dagster-managed pipeline | Via Dagster |

## Dagster (orchestration/)

- `orchestration/assets.py`: Dagster asset definitions + schedules
- Currently 0/1 replicas (scaffolded, not actively used)
- **Known issue**: Dagster uses Hadoop Iceberg catalog (`s3a://lakehouse/warehouse`) while pipeline uses JDBC catalog (`s3://cryptoprice/iceberg`). Catalog mismatch — Dagster may not see streaming tables.

## Known Issues

- **Catalog mismatch**: Dagster assets vs pipeline catalog config differ
- **spark-submit**: Currently 0 replicas — streaming job must be submitted manually
- **Exchange field**: Spark ticker dedup omits `exchange` — should key on `[exchange, symbol, timestamp]`
- **Trino query performance**: Large Iceberg tables with many small Parquet files need compaction
