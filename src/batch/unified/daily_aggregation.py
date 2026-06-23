"""
Unified Daily Aggregation
Aggregates 1h → 4h → 1d → 1w klines in ONE pass
Reduces I/O from 4 operations to 1
"""
import os
import sys
from pathlib import Path
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, first, sum as _sum, avg, max as _max, min as _min,
    lit, current_timestamp, to_date, from_unixtime, window, when, stddev
)
import logging
from datetime import datetime

PROJECT_DIR = Path(os.environ.get("CRYPTO_PROJECT_DIR", "/app"))
sys.path.insert(0, str(PROJECT_DIR / "src"))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def create_spark_session():
    """Create Spark session with Iceberg config"""
    return SparkSession.builder \
        .appName("Unified_Daily_Aggregation") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
        .config("spark.sql.catalog.iceberg_catalog", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.iceberg_catalog.type", "hadoop") \
        .config("spark.sql.catalog.iceberg_catalog.warehouse", "s3a://cryptoprice/warehouse") \
        .config("spark.sql.catalog.iceberg_catalog.io-impl", "org.apache.iceberg.aws.s3.S3FileIO") \
        .config("spark.hadoop.fs.s3a.endpoint", os.getenv("MINIO_ENDPOINT", "http://minio:9000")
        .config("spark.hadoop.fs.s3a.access.key", os.getenv("MINIO_ACCESS_KEY", "")
        .config("spark.hadoop.fs.s3a.secret.key", os.getenv("MINIO_SECRET_KEY", "")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider") \
        .config("spark.sql.catalog.iceberg_catalog.client.region", "us-east-1") \
        .config("spark.sql.catalog.iceberg_catalog.s3.endpoint", os.getenv("MINIO_ENDPOINT", "http://minio:9000")
        .config("spark.sql.catalog.iceberg_catalog.s3.access-key-id", os.getenv("MINIO_ACCESS_KEY", "")
        .config("spark.sql.catalog.iceberg_catalog.s3.secret-access-key", os.getenv("MINIO_SECRET_KEY", "")
        .getOrCreate()


def create_gold_tables(spark: SparkSession):
    """Create Gold symbol_stats_daily table"""
    spark.sql("""
        CREATE TABLE IF NOT EXISTS iceberg.crypto_lakehouse.symbol_stats_daily (
            symbol STRING,
            date DATE,
            open_price DOUBLE,
            high_price DOUBLE,
            low_price DOUBLE,
            close_price DOUBLE,
            volume_24h DOUBLE,
            change_pct_24h DOUBLE,
            volatility DOUBLE,
            avg_spread_pct DOUBLE,
            trade_count BIGINT,
            price_range_pct DOUBLE
        ) USING iceberg
        PARTITIONED BY (date)
    """)
    logger.info("Created gold.symbol_stats_daily table")


def aggregate_long_timeframes(spark: SparkSession):
    """
    Aggregate 1h → 4h → 1d → 1w in ONE pass
    Reduces I/O from 4 reads to 1 read
    """
    logger.info("Aggregating long timeframes (1h → 4h → 1d → 1w)...")

    # Read 1h klines from Silver
    kline_1h = spark.table("iceberg.crypto_lakehouse.kline_multi_timeframe") \
                   .filter(col("interval") == "1h")

    # Cache for multiple aggregations
    kline_1h.cache()

    # Aggregate 1h → 4h
    logger.info("  Aggregating 1h → 4h...")
    kline_4h = kline_1h.groupBy(
        "symbol",
        window(from_unixtime(col("event_time") / 1000), "4 hours").alias("time_window")
    ).agg(
        first("open_price").alias("open_price"),
        _max("high_price").alias("high_price"),
        _min("low_price").alias("low_price"),
        first(col("close_price"), ignorenulls=True).alias("close_price"),
        _sum("volume").alias("volume"),
        _sum("trade_count").alias("trade_count")
    ).select(
        (col("time_window.start").cast("long") * 1000).alias("event_time"),
        col("symbol"),
        lit("4h").alias("interval"),
        col("open_price"),
        col("high_price"),
        col("low_price"),
        col("close_price"),
        col("volume"),
        col("trade_count"),
        lit(True).alias("is_closed"),
        lit(100).alias("quality_score"),
        current_timestamp().alias("last_updated"),
        to_date(col("time_window.start")).alias("_partition_date")
    )

    # Cache 4h for next aggregation
    kline_4h.cache()

    # Aggregate 4h → 1d (from in-memory 4h)
    logger.info("  Aggregating 4h → 1d...")
    kline_1d = kline_4h.groupBy(
        "symbol",
        window(from_unixtime(col("event_time") / 1000), "1 day").alias("time_window")
    ).agg(
        first("open_price").alias("open_price"),
        _max("high_price").alias("high_price"),
        _min("low_price").alias("low_price"),
        first(col("close_price"), ignorenulls=True).alias("close_price"),
        _sum("volume").alias("volume"),
        _sum("trade_count").alias("trade_count")
    ).select(
        (col("time_window.start").cast("long") * 1000).alias("event_time"),
        col("symbol"),
        lit("1d").alias("interval"),
        col("open_price"),
        col("high_price"),
        col("low_price"),
        col("close_price"),
        col("volume"),
        col("trade_count"),
        lit(True).alias("is_closed"),
        lit(100).alias("quality_score"),
        current_timestamp().alias("last_updated"),
        to_date(col("time_window.start")).alias("_partition_date")
    )

    # Cache 1d for next aggregation
    kline_1d.cache()

    # Aggregate 1d → 1w (from in-memory 1d)
    logger.info("  Aggregating 1d → 1w...")
    kline_1w = kline_1d.groupBy(
        "symbol",
        window(from_unixtime(col("event_time") / 1000), "7 days").alias("time_window")
    ).agg(
        first("open_price").alias("open_price"),
        _max("high_price").alias("high_price"),
        _min("low_price").alias("low_price"),
        first(col("close_price"), ignorenulls=True).alias("close_price"),
        _sum("volume").alias("volume"),
        _sum("trade_count").alias("trade_count")
    ).select(
        (col("time_window.start").cast("long") * 1000).alias("event_time"),
        col("symbol"),
        lit("1w").alias("interval"),
        col("open_price"),
        col("high_price"),
        col("low_price"),
        col("close_price"),
        col("volume"),
        col("trade_count"),
        lit(True).alias("is_closed"),
        lit(100).alias("quality_score"),
        current_timestamp().alias("last_updated"),
        to_date(col("time_window.start")).alias("_partition_date")
    )

    # Write all timeframes
    logger.info("  Writing 4h candles...")
    kline_4h.writeTo("iceberg.crypto_lakehouse.kline_multi_timeframe").append()
    count_4h = kline_4h.count()

    logger.info("  Writing 1d candles...")
    kline_1d.writeTo("iceberg.crypto_lakehouse.kline_multi_timeframe").append()
    count_1d = kline_1d.count()

    logger.info("  Writing 1w candles...")
    kline_1w.writeTo("iceberg.crypto_lakehouse.kline_multi_timeframe").append()
    count_1w = kline_1w.count()

    # Unpersist caches
    kline_1h.unpersist()
    kline_4h.unpersist()
    kline_1d.unpersist()

    logger.info(f"Aggregated: 4h={count_4h}, 1d={count_1d}, 1w={count_1w}")
    return count_4h + count_1d + count_1w


def calculate_symbol_stats_daily(spark: SparkSession):
    """Calculate daily statistics for all symbols"""
    logger.info("Calculating symbol_stats_daily...")

    today = datetime.now().strftime("%Y-%m-%d")

    # Get 1d candles
    kline_df = spark.table("iceberg.crypto_lakehouse.kline_multi_timeframe") \
                   .filter((col("interval") == "1d") & (col("_partition_date") == today))

    # Get ticker data for spread
    ticker_df = spark.table("iceberg.crypto_lakehouse.ticker_unified") \
                    .filter(col("_partition_date") == today)

    # Calculate volatility
    volatility = ticker_df.groupBy("symbol").agg(
        stddev("price_mid").alias("volatility"),
        avg("spread_pct").alias("avg_spread_pct")
    )

    # Join kline with volatility
    stats = kline_df.join(volatility, "symbol", "left")

    # Calculate metrics
    result = stats.select(
        col("symbol"),
        lit(today).cast("date").alias("date"),
        col("open_price"),
        col("high_price"),
        col("low_price"),
        col("close_price"),
        col("volume").alias("volume_24h"),
        when((col("open_price") > 0),
             ((col("close_price") - col("open_price")) / col("open_price")) * 100)
        .otherwise(0).alias("change_pct_24h"),
        col("volatility"),
        col("avg_spread_pct"),
        col("trade_count"),
        when((col("low_price") > 0),
             ((col("high_price") - col("low_price")) / col("low_price")) * 100)
        .otherwise(0).alias("price_range_pct")
    )

    # Write to Gold
    result.writeTo("iceberg.crypto_lakehouse.symbol_stats_daily").append()

    count = result.count()
    logger.info(f"Calculated daily stats for {count} symbols")
    return count


def main():
    """Main daily aggregation pipeline"""
    logger.info("=" * 80)
    logger.info("Starting Unified Daily Aggregation")
    logger.info("=" * 80)

    spark = create_spark_session()

    try:
        # Create Gold tables
        create_gold_tables(spark)

        # Aggregate long timeframes (1h → 4h → 1d → 1w)
        kline_count = aggregate_long_timeframes(spark)

        # Calculate daily symbol statistics
        stats_count = calculate_symbol_stats_daily(spark)

        # Summary
        logger.info("=" * 80)
        logger.info("Unified Daily Aggregation completed successfully")
        logger.info(f"  Kline records: {kline_count}")
        logger.info(f"  Symbol stats: {stats_count}")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Daily aggregation failed: {e}", exc_info=True)
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
