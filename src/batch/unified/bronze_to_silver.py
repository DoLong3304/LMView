"""
Unified Bronze → Silver Transformation
Consolidates ticker transformation + kline aggregation into single job
Reduces I/O from 4 reads → 2 reads
"""
import os
import sys
from pathlib import Path
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, first, sum as _sum, avg, max as _max, min as _min,
    when, lit, current_timestamp, to_date, from_unixtime,
    window, expr, row_number, abs as _abs, array_distinct
)
from pyspark.sql.window import Window
import logging

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
        .appName("Unified_Bronze_to_Silver") \
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


def create_silver_tables(spark: SparkSession):
    """Create Silver tables if not exist"""
    # Ticker unified
    spark.sql("""
        CREATE TABLE IF NOT EXISTS iceberg.crypto_lakehouse.ticker_unified (
            event_time BIGINT,
            symbol STRING,
            price_binance DOUBLE,
            price_okx DOUBLE,
            price_mid DOUBLE,
            volume_binance DOUBLE,
            volume_okx DOUBLE,
            volume_total DOUBLE,
            spread_pct DOUBLE,
            quality_score INT,
            last_updated TIMESTAMP,
            _partition_date DATE
        ) USING iceberg
        PARTITIONED BY (_partition_date)
    """)

    # Kline multi-timeframe
    spark.sql("""
        CREATE TABLE IF NOT EXISTS iceberg.crypto_lakehouse.kline_multi_timeframe (
            event_time BIGINT,
            symbol STRING,
            `interval` STRING,
            open_price DOUBLE,
            high_price DOUBLE,
            low_price DOUBLE,
            close_price DOUBLE,
            volume DOUBLE,
            trade_count BIGINT,
            is_closed BOOLEAN,
            quality_score INT,
            last_updated TIMESTAMP,
            _partition_date DATE
        ) USING iceberg
        PARTITIONED BY (_partition_date, `interval`)
    """)

    logger.info("Created Silver tables")


def transform_ticker(spark: SparkSession):
    """Transform Bronze ticker → Silver ticker_unified"""
    logger.info("Transforming ticker data...")

    # Read Bronze ticker
    bronze_df = spark.table("iceberg.crypto_lakehouse.ticker")

    # Deduplicate by (symbol, event_time, exchange)
    window_spec = Window.partitionBy("symbol", "event_time", "exchange").orderBy(col("ingestion_time").desc())
    deduped = bronze_df.withColumn("row_num", row_number().over(window_spec)) \
                      .filter(col("row_num") == 1) \
                      .drop("row_num")

    # Validate price ranges
    validated = deduped.filter(
        (col("price") > 0) &
        (col("price") < 1000000) &
        (col("volume") >= 0)
    )

    # Pivot by exchange
    unified = validated.groupBy("symbol", "event_time").agg(
        first(when(col("exchange") == "binance", col("price"))).alias("price_binance"),
        first(when(col("exchange") == "okx", col("price"))).alias("price_okx"),
        first(when(col("exchange") == "binance", col("volume"))).alias("volume_binance"),
        first(when(col("exchange") == "okx", col("volume"))).alias("volume_okx")
    )

    # Calculate mid-price
    unified = unified.withColumn(
        "price_mid",
        when(col("price_binance").isNotNull() & col("price_okx").isNotNull(),
             (col("price_binance") + col("price_okx")) / 2)
        .when(col("price_binance").isNotNull(), col("price_binance"))
        .when(col("price_okx").isNotNull(), col("price_okx"))
        .otherwise(None)
    )

    # Calculate total volume
    unified = unified.withColumn(
        "volume_total",
        when(col("volume_binance").isNotNull() & col("volume_okx").isNotNull(),
             col("volume_binance") + col("volume_okx"))
        .when(col("volume_binance").isNotNull(), col("volume_binance"))
        .when(col("volume_okx").isNotNull(), col("volume_okx"))
        .otherwise(0)
    )

    # Calculate spread percentage
    unified = unified.withColumn(
        "spread_pct",
        when(col("price_binance").isNotNull() & col("price_okx").isNotNull() & (col("price_mid") > 0),
             (_abs(col("price_binance") - col("price_okx")) / col("price_mid")) * 100)
        .otherwise(0)
    )

    # Quality score
    unified = unified.withColumn(
        "quality_score",
        when(col("price_binance").isNotNull() & col("price_okx").isNotNull(), 100)
        .when(col("price_binance").isNotNull() | col("price_okx").isNotNull(), 50)
        .otherwise(0)
    )

    # Add metadata
    unified = unified.withColumn("last_updated", current_timestamp()) \
                    .withColumn("_partition_date", to_date(from_unixtime(col("event_time") / 1000)))

    # Write to Silver
    unified.writeTo("iceberg.crypto_lakehouse.ticker_unified").append()

    count = unified.count()
    logger.info(f"Transformed {count} ticker records to Silver")
    return count


def aggregate_klines_unified(spark: SparkSession):
    """
    Aggregate klines in ONE pass: 1m → 5m → 15m → 1h
    Reduces I/O from 4 operations to 1
    """
    logger.info("Aggregating klines (1m → 5m → 15m → 1h)...")

    # Read Bronze 1m klines
    bronze_1m = spark.table("iceberg.crypto_lakehouse.kline") \
                    .filter(col("interval") == "1m")

    # Aggregate 1m → 5m
    logger.info("  Aggregating 1m → 5m...")
    kline_5m = bronze_1m.groupBy(
        "symbol",
        window(from_unixtime(col("event_time") / 1000), "5 minutes").alias("time_window")
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
        lit("5m").alias("interval"),
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

    # Cache 5m for next aggregation
    kline_5m.cache()

    # Aggregate 5m → 15m (from in-memory 5m)
    logger.info("  Aggregating 5m → 15m...")
    kline_15m = kline_5m.groupBy(
        "symbol",
        window(from_unixtime(col("event_time") / 1000), "15 minutes").alias("time_window")
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
        lit("15m").alias("interval"),
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

    # Cache 15m for next aggregation
    kline_15m.cache()

    # Aggregate 15m → 1h (from in-memory 15m)
    logger.info("  Aggregating 15m → 1h...")
    kline_1h = kline_15m.groupBy(
        "symbol",
        window(from_unixtime(col("event_time") / 1000), "1 hour").alias("time_window")
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
        lit("1h").alias("interval"),
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

    # Write all timeframes to Silver
    logger.info("  Writing 5m candles...")
    kline_5m.writeTo("iceberg.crypto_lakehouse.kline_multi_timeframe").append()
    count_5m = kline_5m.count()

    logger.info("  Writing 15m candles...")
    kline_15m.writeTo("iceberg.crypto_lakehouse.kline_multi_timeframe").append()
    count_15m = kline_15m.count()

    logger.info("  Writing 1h candles...")
    kline_1h.writeTo("iceberg.crypto_lakehouse.kline_multi_timeframe").append()
    count_1h = kline_1h.count()

    # Unpersist cache
    kline_5m.unpersist()
    kline_15m.unpersist()

    logger.info(f"Aggregated klines: 5m={count_5m}, 15m={count_15m}, 1h={count_1h}")
    return count_5m + count_15m + count_1h


def main():
    """Main ETL pipeline"""
    logger.info("=" * 80)
    logger.info("Starting Unified Bronze → Silver ETL")
    logger.info("=" * 80)

    spark = create_spark_session()

    try:
        # Create tables
        create_silver_tables(spark)

        # Transform ticker
        ticker_count = transform_ticker(spark)

        # Aggregate klines (1m → 5m → 15m → 1h in ONE pass)
        kline_count = aggregate_klines_unified(spark)

        # Summary
        logger.info("=" * 80)
        logger.info("Unified Bronze → Silver ETL completed successfully")
        logger.info(f"  Ticker records: {ticker_count}")
        logger.info(f"  Kline records: {kline_count}")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"ETL failed: {e}", exc_info=True)
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    main()

