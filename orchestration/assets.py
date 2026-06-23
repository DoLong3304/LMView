"""
Dagster Assets for Medallion Architecture & News Sentiment
Orchestrates Bronze → Silver → Gold transformations
"""
from dagster import asset, AssetExecutionContext, schedule, define_asset_job, Definitions
from pyspark.sql import SparkSession
import subprocess
import sys
import os
from pathlib import Path

# Add src to path
PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR / "src"))

from lakehouse.silver.transformations import SilverTickerTransformation, SilverKlineAggregation
from lakehouse.gold.aggregations import GoldMarketOverview, GoldSymbolStatistics, GoldSectorPerformance
import logging

SPARK_MASTER_URL = os.getenv("SPARK_MASTER_URL", os.getenv("SPARK_MASTER", "spark://spark-master:7077"))
SPARK_SUBMIT = os.getenv("SPARK_SUBMIT", "/opt/spark/bin/spark-submit")
GOLD_TRINO_JOB_PATH = "/app/src/lakehouse/gold_aggregator_trino.py"
SPARK_PACKAGES = (
    "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.2,"
    "org.apache.iceberg:iceberg-aws-bundle:1.5.2,"
    "org.apache.hadoop:hadoop-aws:3.3.4,"
    "org.postgresql:postgresql:42.7.2,"
    "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.5,"
    "org.apache.spark:spark-avro_2.12:3.5.5"
)


def get_spark_session() -> SparkSession:
    """Create Spark session with Iceberg support.

    Registers the iceberg catalog under TWO names so that the existing
    SQL in src/lakehouse/gold/*.py (`iceberg.crypto_lakehouse.gold_*`)
    and the older pipeline code in src/lakehouse/pipeline.py
    (`iceberg_catalog.bronze.*`) both resolve to the same Hadoop catalog
    backed by the s3a://lmview-warehouse/warehouse S3 bucket.

    We also pass `spark.jars.packages` so the iceberg + s3 jars are
    available on the classpath of the local SparkSession. Without these
    the session would fail with
    `ClassNotFoundException: IcebergSparkSessionExtensions`.
    """
    return SparkSession.builder \
        .appName("Medallion_Pipeline") \
        .config("spark.jars.packages", SPARK_PACKAGES) \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
        .config("spark.sql.catalog.iceberg_catalog", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.iceberg_catalog.type", "hadoop") \
        .config("spark.sql.catalog.iceberg_catalog.warehouse", "s3a://lakehouse/warehouse") \
        .config("spark.sql.catalog.iceberg", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.iceberg.type", "hadoop") \
        .config("spark.sql.catalog.iceberg.warehouse", "s3a://lakehouse/warehouse") \
        .getOrCreate()


# ============================================================================
# SILVER LAYER ASSETS
# ============================================================================

@asset(group_name="silver", compute_kind="spark")
def silver_ticker_unified(context: AssetExecutionContext):
    """
    Transform Bronze ticker → Silver unified ticker
    - Deduplicates data
    - Calculates mid-price from Binance + OKX
    - Quality scoring
    """
    spark = get_spark_session()
    transformer = SilverTickerTransformation(spark)

    # Create table if not exists
    transformer.create_table()

    # Transform today's data
    transformer.transform()

    context.log.info("Silver ticker_unified transformation complete")


@asset(group_name="silver", compute_kind="spark")
def silver_kline_5m(context: AssetExecutionContext):
    """Aggregate 1m → 5m candles"""
    spark = get_spark_session()
    aggregator = SilverKlineAggregation(spark)

    aggregator.create_table()
    aggregator.aggregate_timeframe(source_interval="1m", target_interval="5m", multiplier=5)

    context.log.info("Silver 5m klines aggregated")


@asset(group_name="silver", compute_kind="spark")
def silver_kline_15m(context: AssetExecutionContext):
    """Aggregate 5m → 15m candles"""
    spark = get_spark_session()
    aggregator = SilverKlineAggregation(spark)

    aggregator.aggregate_timeframe(source_interval="5m", target_interval="15m", multiplier=3)

    context.log.info("Silver 15m klines aggregated")


@asset(group_name="silver", compute_kind="spark")
def silver_kline_1h(context: AssetExecutionContext):
    """Aggregate 15m → 1h candles"""
    spark = get_spark_session()
    aggregator = SilverKlineAggregation(spark)

    aggregator.aggregate_timeframe(source_interval="15m", target_interval="1h", multiplier=4)

    context.log.info("Silver 1h klines aggregated")


@asset(group_name="silver", compute_kind="spark")
def silver_kline_4h(context: AssetExecutionContext):
    """Aggregate 1h → 4h candles"""
    spark = get_spark_session()
    aggregator = SilverKlineAggregation(spark)

    aggregator.aggregate_timeframe(source_interval="1h", target_interval="4h", multiplier=4)

    context.log.info("Silver 4h klines aggregated")


@asset(group_name="silver", compute_kind="spark")
def silver_kline_1d(context: AssetExecutionContext):
    """Aggregate 4h → 1d candles"""
    spark = get_spark_session()
    aggregator = SilverKlineAggregation(spark)

    aggregator.aggregate_timeframe(source_interval="4h", target_interval="1d", multiplier=6)

    context.log.info("Silver 1d klines aggregated")


@asset(group_name="silver", compute_kind="spark")
def silver_kline_1w(context: AssetExecutionContext):
    """Aggregate 1d → 1w candles"""
    spark = get_spark_session()
    aggregator = SilverKlineAggregation(spark)

    aggregator.aggregate_timeframe(source_interval="1d", target_interval="1w", multiplier=7)

    context.log.info("Silver 1w klines aggregated")


# ============================================================================
# GOLD LAYER ASSETS
# ============================================================================

@asset(group_name="gold", compute_kind="spark", deps=[silver_ticker_unified])
def gold_market_overview(context: AssetExecutionContext):
    """
    Calculate market overview metrics
    - Top 10 gainers/losers
    - Total volume
    - Market statistics
    """
    spark = get_spark_session()
    calculator = GoldMarketOverview(spark)

    calculator.create_table()
    calculator.calculate()

    context.log.info("Gold market_overview calculated")


@asset(group_name="gold", compute_kind="spark", deps=[silver_kline_1d, silver_ticker_unified])
def gold_symbol_statistics(context: AssetExecutionContext):
    """
    Calculate per-symbol daily statistics
    - OHLCV
    - Volatility
    - Change %
    """
    spark = get_spark_session()
    calculator = GoldSymbolStatistics(spark)

    calculator.create_table()

    # Calculate for today
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    calculator.calculate(date=today)

    context.log.info("Gold symbol_statistics calculated")


@asset(group_name="gold", compute_kind="spark", deps=[silver_ticker_unified])
def gold_sector_performance(context: AssetExecutionContext):
    """
    Calculate sector-level performance
    - Large/Mid/Small cap performance
    - Top symbols per sector
    """
    spark = get_spark_session()
    calculator = GoldSectorPerformance(spark)

    calculator.create_table()
    calculator.calculate()

    context.log.info("Gold sector_performance calculated")


# ============================================================================
# NEWS SENTIMENT ASSETS
# ============================================================================

@asset(group_name="news", compute_kind="python")
def news_sentiment_multi_source(context: AssetExecutionContext):
    """
    Fetch news from 10+ sources and analyze sentiment
    - CryptoPanic, CoinDesk, CoinTelegraph, Decrypt, The Block
    - Bitcoin Magazine, CryptoSlate, BeInCrypto, NewsBTC, U.Today
    - Bitcoinist, CryptoNews
    """
    from news.enhanced_scraper import MultiSourceNewsScraper
    from news.sentiment_analyzer import SentimentAnalyzer
    from common.kafka_client import get_kafka_producer
    from common.avro_serializer import AvroSerializer

    # Initialize scraper
    api_key = os.getenv("CRYPTOPANIC_API_KEY")
    scraper = MultiSourceNewsScraper(cryptopanic_api_key=api_key)

    # Fetch recent news (last 5 minutes)
    articles = scraper.fetch_recent(hours=0.1, articles_per_source=5)  # 6 minutes = 0.1 hours

    if not articles:
        context.log.warning("No articles fetched")
        return

    # Analyze sentiment
    analyzer = SentimentAnalyzer()
    for article in articles:
        sentiment = analyzer.analyze(article["title"] + " " + article["content"])
        article["sentiment_score"] = sentiment["compound"]
        article["sentiment_label"] = sentiment["label"]

    # Publish to Kafka
    producer = get_kafka_producer()
    serializer = AvroSerializer("news")

    for article in articles:
        # Add timestamp
        article["event_time"] = article["published_at"]

        # Serialize and send
        key = article["url"].encode("utf-8")
        value = serializer.serialize(article)
        producer.send("crypto_news_sentiment", key=key, value=value)

    producer.flush()

    context.log.info(f"Published {len(articles)} articles to Kafka")
    context.log.info(f"Sources: {set(a['source'] for a in articles)}")


# ---------------------------------------------------------------------------
# gold_news_market_impact depends on news_sentiment_multi_source which is
# defined above. Placed here (after the @asset def) so Python sees the
# forward reference at decoration time.
# ---------------------------------------------------------------------------
@asset(group_name="gold", compute_kind="spark", deps=[silver_ticker_unified, news_sentiment_multi_source])
def gold_news_market_impact(context: AssetExecutionContext):
    """
    Join news sentiment scores with realized price changes (1h/4h/24h).
    Per v0.24.5 (Task 4): we use the canonical Trino table schema defined
    in src/lakehouse/gold_schema_manifest.py and the pure-function
    builder in src/lakehouse/gold/news_impact.py.

    Output: iceberg.gold.gold_news_market_impact (idempotent MERGE).
    Reference exchange: binance (cross-venue divergence <50bps).
    """
    from lakehouse.gold.news_impact import compute_gold_news_market_impact
    spark = get_spark_session()
    context.log.info("Computing gold_news_market_impact (Task 4 / v0.24.5)...")
    rows_written = compute_gold_news_market_impact(spark, lookback_hours=48)
    context.log.info(f"gold_news_market_impact updated: {rows_written} rows")


# ============================================================================
# JOBS & SCHEDULES
# ============================================================================

# Silver transformation job (every 5 minutes)
silver_transformation_job = define_asset_job(
    name="silver_transformation",
    selection=[
        silver_ticker_unified,
        silver_kline_5m,
        silver_kline_15m,
        silver_kline_1h
    ]
)

@schedule(
    job=silver_transformation_job,
    cron_schedule="*/5 * * * *"  # Every 5 minutes
)
def silver_transformation_schedule():
    return {}


# Gold aggregation job (every 5 minutes)
gold_aggregation_job = define_asset_job(
    name="gold_aggregation",
    selection=[
        gold_market_overview,
        gold_symbol_statistics,
        gold_sector_performance,
        gold_news_market_impact,
    ]
)

@schedule(
    job=gold_aggregation_job,
    cron_schedule="*/5 * * * *"  # Every 5 minutes
)
def gold_aggregation_schedule():
    return {}


# Daily aggregation job (for 4h, 1d, 1w candles)
daily_aggregation_job = define_asset_job(
    name="daily_aggregation",
    selection=[
        silver_kline_4h,
        silver_kline_1d,
        silver_kline_1w
    ]
)

@schedule(
    job=daily_aggregation_job,
    cron_schedule="0 0 * * *"  # Daily at midnight
)
def daily_aggregation_schedule():
    return {}


# News sentiment job (every 5 minutes)
news_sentiment_job = define_asset_job(
    name="news_sentiment",
    selection=[news_sentiment_multi_source]
)

@schedule(
    job=news_sentiment_job,
    cron_schedule="*/5 * * * *"  # Every 5 minutes
)
def news_sentiment_schedule():
    return {}


# ============================================================================
# ADVANCED GOLD METRICS ASSETS
# ============================================================================
# --- DEPRECATED (v0.24.4 P1 fix) -----------------------------------------
# These Spark-based assets were running every 5 minutes and producing
# tables that NO API endpoint reads. The API consumes the Trino-based
# ``gold_*`` tables written by ``compute_gold_layer`` (see below).
#
# See src/lakehouse/gold_schema_manifest.py for the canonical schema list
# and DEPRECATED_SPARK_TABLES for the full deprecation rationale.
#
# The code is KEPT (not deleted) so future contributors can:
#   1. Re-align the Spark output to the canonical schema and re-enable.
#   2. Use it as a reference for how the per-row gold_* tables are derived
#      in a different compute path.
#
# To re-enable: restore the @asset decorators and re-add to
# ``gold_advanced_job`` selection below.
# --------------------------------------------------------------------------

# @asset(group_name="gold_advanced", compute_kind="spark", deps=[silver_ticker_unified])
def gold_market_dominance_deprecated(context: AssetExecutionContext):
    """DEPRECATED: see gold_schema_manifest.DEPRECATED_SPARK_TABLES."""
    from lakehouse.gold.market_metrics import GoldMarketDominance

    spark = get_spark_session()
    calculator = GoldMarketDominance(spark)

    calculator.create_table()
    calculator.calculate()

    context.log.info("Gold market_dominance calculated")


# @asset(group_name="gold_advanced", compute_kind="spark", deps=[silver_ticker_unified])
def gold_volatility_ranking_deprecated(context: AssetExecutionContext):
    """DEPRECATED: see gold_schema_manifest.DEPRECATED_SPARK_TABLES."""
    from lakehouse.gold.market_metrics import GoldVolatilityRanking

    spark = get_spark_session()
    calculator = GoldVolatilityRanking(spark)

    calculator.create_table()
    calculator.calculate()

    context.log.info("Gold volatility_ranking calculated")


# @asset(group_name="gold_advanced", compute_kind="spark", deps=[silver_ticker_unified])
def gold_movers_ranking_deprecated(context: AssetExecutionContext):
    """DEPRECATED: see gold_schema_manifest.DEPRECATED_SPARK_TABLES."""
    from lakehouse.gold.market_metrics import GoldMoversRanking

    spark = get_spark_session()
    calculator = GoldMoversRanking(spark)

    calculator.create_table()
    calculator.calculate()

    context.log.info("Gold movers_ranking calculated")


@asset(
    group_name="gold_layer",
    compute_kind="python",
    description="Compute gold overview tables from current crypto_lakehouse tables every 5 minutes",
)
def compute_gold_layer(context: AssetExecutionContext):
    cmd = ["python3", GOLD_TRINO_JOB_PATH]
    context.log.info("Running gold aggregation job: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        context.log.error(result.stderr[-2000:])
        context.log.error(result.stdout[-2000:])
        raise RuntimeError(f"Gold aggregation failed: {result.stderr[-500:] or result.stdout[-500:]}")
    context.log.info(result.stdout[-2000:])
    return {"status": "success"}


# @asset(group_name="gold_advanced", compute_kind="spark", deps=[silver_kline_1h])
def gold_momentum_indicators_deprecated(context: AssetExecutionContext):
    """DEPRECATED: gold_momentum_indicators is now produced by the Trino
    job ``compute_gold_layer`` (src/lakehouse/gold_aggregator_trino.py).
    See gold_schema_manifest.DEPRECATED_SPARK_TABLES.
    """
    import subprocess

    result = subprocess.run(
        ["spark-submit", "/app/src/batch/calculate_indicators.py"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        context.log.error(f"Indicators calculation failed: {result.stderr}")
        raise RuntimeError(f"Indicators calculation failed")

    context.log.info("Gold momentum_indicators calculated")


@asset(
    group_name="gold_layer",
    compute_kind="python",
    description="Aggregate daily news sentiment per symbol into Iceberg gold via Trino",
    deps=[compute_gold_layer],
)
def compute_news_sentiment_daily(context: AssetExecutionContext):
    """
    Aggregate sentiment scores from PostgreSQL → iceberg.crypto_lakehouse.gold_news_sentiment_daily.
    Runs after compute_gold_layer. Reads from news_articles, groups by symbol/day, writes to Trino.
    """
    import asyncio
    import json
    import time
    import urllib.request

    TRINO_URL = "http://trino:8080/v1/statement"
    HEADERS = {
        "X-Trino-User": "dagster-gold-layer",
        "X-Trino-Catalog": "iceberg",
        "X-Trino-Schema": "crypto_lakehouse",
    }

    def run_trino_query(sql: str) -> list:
        data = sql.encode("utf-8")
        req = urllib.request.Request(TRINO_URL, data=data, headers=HEADERS)
        with urllib.request.urlopen(req) as resp:
            payload = json.load(resp)
        next_uri = payload.get("nextUri")
        while next_uri:
            with urllib.request.urlopen(next_uri) as resp:
                payload = json.load(resp)
            if payload.get("error"):
                raise RuntimeError(payload["error"])
            next_uri = payload.get("nextUri")
            time.sleep(0.05)
        if payload.get("error"):
            raise RuntimeError(payload["error"])
        return payload.get("data", [])

    async def _aggregate():
        import asyncpg

        pg_conn = await asyncpg.connect(
            host=os.getenv("POSTGRES_HOST", "postgres"),
            database=os.getenv("POSTGRES_DB", "lmview_db"),
            user=os.getenv("POSTGRES_USER", "lmview"),
            password=os.getenv("POSTGRES_PASSWORD", "lmview"),
        )
        try:
            rows = await pg_conn.fetch(
                """
                SELECT
                    date_trunc('day', published_at) AS date,
                    UNNEST(symbols_mentioned) AS symbol,
                    AVG(COALESCE(sentiment_score, 0)) AS avg_sentiment,
                    COUNT(*) AS article_count,
                    SUM(CASE WHEN sentiment_label = 'bullish' THEN 1 ELSE 0 END) AS bullish_count,
                    SUM(CASE WHEN sentiment_label = 'bearish' THEN 1 ELSE 0 END) AS bearish_count
                FROM news_articles
                WHERE symbols_mentioned IS NOT NULL
                  AND array_length(symbols_mentioned, 1) > 0
                  AND published_at >= NOW() - INTERVAL '7 days'
                GROUP BY 1, 2
                ORDER BY 1 DESC, 3 DESC
                """
            )
            return [dict(r) for r in rows]
        finally:
            await pg_conn.close()

    context.log.info("Starting news sentiment daily aggregation")
    rows = asyncio.run(_aggregate())
    context.log.info("Aggregated %d symbol-day pairs from PostgreSQL", len(rows))

    # Ensure table exists
    run_trino_query(
        """
        CREATE TABLE IF NOT EXISTS gold_news_sentiment_daily (
            date TIMESTAMP(6) WITH TIME ZONE,
            symbol VARCHAR,
            avg_sentiment DOUBLE,
            article_count BIGINT,
            bullish_count BIGINT,
            bearish_count BIGINT,
            _partition_date DATE
        ) WITH (format='PARQUET', partitioning=ARRAY['_partition_date'])
        """
    )

    # Delete old data for the period we're about to rewrite
    run_trino_query(
        "DELETE FROM gold_news_sentiment_daily WHERE _partition_date >= CURRENT_DATE - INTERVAL '7' day"
    )

    # Insert new aggregates
    for row in rows:
        date_str = row["date"].strftime("%Y-%m-%d %H:%M:%S")
        sql = f"""
        INSERT INTO gold_news_sentiment_daily
        VALUES (
            TIMESTAMP '{date_str}' AT TIME ZONE 'UTC',
            '{row['symbol']}',
            {float(row['avg_sentiment'] or 0)},
            {int(row['article_count'] or 0)},
            {int(row['bullish_count'] or 0)},
            {int(row['bearish_count'] or 0)},
            DATE '{row['date'].date().isoformat()}'
        )
        """
        run_trino_query(sql)

    context.log.info("Wrote %d rows to gold_news_sentiment_daily", len(rows))
    return {"rows_written": len(rows)}


# Advanced gold metrics job (every 5 minutes)
# --- v0.24.4 P1 fix ---
# Spark-based gold_advanced assets are DEPRECATED (see comment block above).
# The canonical Gold path is the Trino job ``compute_gold_layer`` which
# is already scheduled in ``gold_layer_job`` below. We keep the job +
# schedule (no-op selection) so existing Dagster deployment configs do
# not break; new contributors will see the deprecation comment first.
gold_advanced_job = define_asset_job(
    name="gold_advanced_metrics",
    selection=[
        # gold_market_dominance,        # DEPRECATED: see gold_schema_manifest
        # gold_volatility_ranking,     # DEPRECATED
        # gold_movers_ranking,         # DEPRECATED
        # gold_momentum_indicators,     # DEPRECATED
        # compute_gold_layer is here for backwards compatibility but the
        # canonical schedule is gold_layer_job (below).
        compute_gold_layer,
    ]
)

@schedule(
    job=gold_advanced_job,
    cron_schedule="*/5 * * * *",  # Every 5 minutes (kept for back-compat)
)
def gold_advanced_schedule():
    """Schedule is a no-op now (Trino path is in gold_layer_job)."""
    return {}


gold_layer_job = define_asset_job(
    name="gold_layer_job",
    selection=[compute_gold_layer, compute_news_sentiment_daily],
)

@schedule(
    job=gold_layer_job,
    cron_schedule="*/5 * * * *"
)
def gold_layer_schedule():
    return {}


defs = Definitions(
    assets=[
        silver_ticker_unified,
        silver_kline_5m,
        silver_kline_15m,
        silver_kline_1h,
        silver_kline_4h,
        silver_kline_1d,
        silver_kline_1w,
        gold_market_overview,
        gold_symbol_statistics,
        gold_sector_performance,
        gold_news_market_impact,
        news_sentiment_multi_source,
        # gold_market_dominance,        # DEPRECATED: see gold_schema_manifest (replaced by /api/market/dominance endpoint)
        # gold_volatility_ranking,     # DEPRECATED
        # gold_movers_ranking,         # DEPRECATED
        # gold_momentum_indicators,    # DEPRECATED
        compute_gold_layer,
        compute_news_sentiment_daily,
    ],
    schedules=[
        silver_transformation_schedule,
        gold_aggregation_schedule,
        daily_aggregation_schedule,
        news_sentiment_schedule,
        gold_advanced_schedule,
        gold_layer_schedule,
    ],
)


