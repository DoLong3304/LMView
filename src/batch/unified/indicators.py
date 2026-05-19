"""
Unified Technical Indicators Calculator
Calculate RSI, MACD, Bollinger Bands in single job
Reads silver.kline_multi_timeframe (1h) ONCE
"""
import os
import sys
from pathlib import Path
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, avg, stddev, lag, when, expr, current_timestamp, to_date, desc
)
from pyspark.sql.window import Window
import logging
from datetime import datetime, timedelta

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
        .appName("Unified_Technical_Indicators") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
        .config("spark.sql.catalog.iceberg_catalog", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.iceberg_catalog.type", "hadoop") \
        .config("spark.sql.catalog.iceberg_catalog.warehouse", "s3a://cryptoprice/warehouse") \
        .config("spark.sql.catalog.iceberg_catalog.io-impl", "org.apache.iceberg.aws.s3.S3FileIO") \
        .config("spark.hadoop.fs.s3a.endpoint", os.getenv("MINIO_ENDPOINT", "http://minio:9000")) \
        .config("spark.hadoop.fs.s3a.access.key", os.getenv("MINIO_ACCESS_KEY", "admin")) \
        .config("spark.hadoop.fs.s3a.secret.key", os.getenv("MINIO_SECRET_KEY", "password")) \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider") \
        .config("spark.sql.catalog.iceberg_catalog.client.region", "us-east-1") \
        .config("spark.sql.catalog.iceberg_catalog.s3.endpoint", os.getenv("MINIO_ENDPOINT", "http://minio:9000")) \
        .config("spark.sql.catalog.iceberg_catalog.s3.path-style-access", "true") \
        .config("spark.sql.catalog.iceberg_catalog.s3.access-key-id", os.getenv("MINIO_ACCESS_KEY", "admin")) \
        .config("spark.sql.catalog.iceberg_catalog.s3.secret-access-key", os.getenv("MINIO_SECRET_KEY", "password")) \
        .getOrCreate()


def create_indicators_table(spark: SparkSession):
    """Create momentum_indicators table"""
    spark.sql("""
        CREATE TABLE IF NOT EXISTS iceberg_catalog.gold.momentum_indicators (
            symbol STRING NOT NULL,
            snapshot_time TIMESTAMP NOT NULL,
            current_price DOUBLE,
            rsi_14 DOUBLE,
            macd DOUBLE,
            macd_signal DOUBLE,
            macd_histogram DOUBLE,
            bb_upper DOUBLE,
            bb_middle DOUBLE,
            bb_lower DOUBLE,
            bb_width DOUBLE,
            volume_sma_20 DOUBLE,
            price_sma_20 DOUBLE,
            price_sma_50 DOUBLE,
            price_ema_12 DOUBLE,
            price_ema_26 DOUBLE,
            _partition_date DATE NOT NULL
        ) USING iceberg
        PARTITIONED BY (_partition_date)
        TBLPROPERTIES (
            'write.format.default' = 'parquet',
            'write.parquet.compression-codec' = 'snappy'
        )
    """)
    logger.info("Created gold.momentum_indicators table")


def calculate_rsi(df, price_col="close_price", period=14):
    """Calculate RSI (Relative Strength Index)"""
    window = Window.partitionBy("symbol").orderBy("event_time")

    # Calculate price changes
    df = df.withColumn("price_change", col(price_col) - lag(price_col, 1).over(window))

    # Separate gains and losses
    df = df.withColumn("gain", when(col("price_change") > 0, col("price_change")).otherwise(0))
    df = df.withColumn("loss", when(col("price_change") < 0, -col("price_change")).otherwise(0))

    # Calculate average gain and loss
    window_period = Window.partitionBy("symbol").orderBy("event_time").rowsBetween(-period + 1, 0)
    df = df.withColumn("avg_gain", avg("gain").over(window_period))
    df = df.withColumn("avg_loss", avg("loss").over(window_period))

    # Calculate RS and RSI
    df = df.withColumn(
        "rs",
        when(col("avg_loss") > 0, col("avg_gain") / col("avg_loss")).otherwise(100)
    )
    df = df.withColumn(
        f"rsi_{period}",
        100 - (100 / (1 + col("rs")))
    )

    return df


def calculate_macd(df, price_col="close_price", fast=12, slow=26, signal=9):
    """Calculate MACD (Moving Average Convergence Divergence)"""
    window = Window.partitionBy("symbol").orderBy("event_time")

    # Calculate EMA approximation using SMA
    window_fast = Window.partitionBy("symbol").orderBy("event_time").rowsBetween(-fast + 1, 0)
    window_slow = Window.partitionBy("symbol").orderBy("event_time").rowsBetween(-slow + 1, 0)

    df = df.withColumn("ema_12", avg(price_col).over(window_fast))
    df = df.withColumn("ema_26", avg(price_col).over(window_slow))

    # MACD line
    df = df.withColumn("macd", col("ema_12") - col("ema_26"))

    # Signal line (EMA of MACD)
    window_signal = Window.partitionBy("symbol").orderBy("event_time").rowsBetween(-signal + 1, 0)
    df = df.withColumn("macd_signal", avg("macd").over(window_signal))

    # Histogram
    df = df.withColumn("macd_histogram", col("macd") - col("macd_signal"))

    return df


def calculate_bollinger_bands(df, price_col="close_price", period=20, std_dev=2):
    """Calculate Bollinger Bands"""
    window = Window.partitionBy("symbol").orderBy("event_time").rowsBetween(-period + 1, 0)

    # Middle band (SMA)
    df = df.withColumn("bb_middle", avg(price_col).over(window))

    # Standard deviation
    df = df.withColumn("bb_std", stddev(price_col).over(window))

    # Upper and lower bands
    df = df.withColumn("bb_upper", col("bb_middle") + (col("bb_std") * std_dev))
    df = df.withColumn("bb_lower", col("bb_middle") - (col("bb_std") * std_dev))

    # Band width (volatility indicator)
    df = df.withColumn("bb_width", col("bb_upper") - col("bb_lower"))

    return df


def calculate_sma(df, price_col="close_price", volume_col="volume", periods=[20, 50]):
    """Calculate Simple Moving Averages"""
    for period in periods:
        window = Window.partitionBy("symbol").orderBy("event_time").rowsBetween(-period + 1, 0)
        df = df.withColumn(f"price_sma_{period}", avg(price_col).over(window))

        if period == 20:
            df = df.withColumn(f"volume_sma_{period}", avg(volume_col).over(window))

    return df


def main():
    """Main calculation pipeline"""
    logger.info("=" * 80)
    logger.info("Starting Unified Technical Indicators Calculation")
    logger.info("=" * 80)

    spark = create_spark_session()

    try:
        # Create table
        create_indicators_table(spark)

        # Read 1h klines from Silver (last 7 days for sufficient history)
        date_7d_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        logger.info(f"Reading 1h klines from {date_7d_ago}...")
        klines_df = spark.table("iceberg_catalog.silver.kline_multi_timeframe") \
                        .filter(
                            (col("interval") == "1h") &
                            (col("_partition_date") >= date_7d_ago)
                        ) \
                        .select(
                            "symbol",
                            "event_time",
                            "close_price",
                            "volume"
                        )

        # Calculate all indicators
        logger.info("Calculating RSI...")
        df = calculate_rsi(klines_df, period=14)

        logger.info("Calculating MACD...")
        df = calculate_macd(df)

        logger.info("Calculating Bollinger Bands...")
        df = calculate_bollinger_bands(df, period=20)

        logger.info("Calculating SMAs...")
        df = calculate_sma(df, periods=[20, 50])

        # Get latest values per symbol
        logger.info("Extracting latest indicators per symbol...")
        window_latest = Window.partitionBy("symbol").orderBy(desc("event_time"))
        latest_df = df.withColumn("rank", expr("row_number() OVER (PARTITION BY symbol ORDER BY event_time DESC)")) \
                     .filter(col("rank") == 1) \
                     .drop("rank")

        # Select final columns
        result_df = latest_df.select(
            "symbol",
            current_timestamp().alias("snapshot_time"),
            col("close_price").alias("current_price"),
            "rsi_14",
            "macd",
            "macd_signal",
            "macd_histogram",
            "bb_upper",
            "bb_middle",
            "bb_lower",
            "bb_width",
            "volume_sma_20",
            "price_sma_20",
            "price_sma_50",
            col("ema_12").alias("price_ema_12"),
            col("ema_26").alias("price_ema_26"),
            to_date(current_timestamp()).alias("_partition_date")
        )

        # Write to Gold
        logger.info("Writing to gold.momentum_indicators...")
        result_df.write \
            .format("iceberg") \
            .mode("overwrite") \
            .option("overwrite-mode", "dynamic") \
            .saveAsTable("iceberg_catalog.gold.momentum_indicators")

        count = result_df.count()

        # Summary
        logger.info("=" * 80)
        logger.info("Unified Technical Indicators completed successfully")
        logger.info(f"  Calculated indicators for {count} symbols")
        logger.info("=" * 80)

        # Show sample
        logger.info("Sample indicators:")
        result_df.orderBy(desc("rsi_14")).show(10, False)

    except Exception as e:
        logger.error(f"Indicator calculation failed: {e}", exc_info=True)
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
