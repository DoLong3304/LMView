"""
Dagster Assets for Medallion Architecture & News Sentiment
Orchestrates Bronze → Silver → Gold transformations
"""
from dagster import asset, AssetExecutionContext, schedule, define_asset_job, ScheduleDefinition
from pyspark.sql import SparkSession
import sys
import os
from pathlib import Path

# Add src to path
PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR / "src"))

from lakehouse.silver.transformations import SilverTickerTransformation, SilverKlineAggregation
from lakehouse.gold.aggregations import GoldMarketOverview, GoldSymbolStatistics, GoldSectorPerformance
from news.multi_source_scraper import MultiSourceNewsScraper
from news.sentiment_analyzer import SentimentAnalyzer
from common.kafka_client import get_kafka_producer
from common.avro_serializer import AvroSerializer
import logging

logger = logging.getLogger(__name__)


def get_spark_session() -> SparkSession:
    """Create Spark session with Iceberg support"""
    return SparkSession.builder \
        .appName("Medallion_Pipeline") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
        .config("spark.sql.catalog.iceberg_catalog", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.iceberg_catalog.type", "hadoop") \
        .config("spark.sql.catalog.iceberg_catalog.warehouse", "s3a://lakehouse/warehouse") \
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
        gold_sector_performance
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
