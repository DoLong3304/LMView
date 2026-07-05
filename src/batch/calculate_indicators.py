"""
Technical Indicators Calculator
Calculate RSI, MACD, Bollinger Bands, and other indicators
"""
import os
import sys
from pathlib import Path
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, avg, stddev, lag, when, expr, current_timestamp, to_date, desc, lit
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
        .appName("Calculate_Technical_Indicators") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
        .config("spark.sql.catalog.iceberg_catalog", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.iceberg_catalog.type", "hadoop") \
        .config("spark.sql.catalog.iceberg_catalog.warehouse", "s3a://lmview-iceberg-storage/warehouse") \
        .config("spark.sql.catalog.iceberg_catalog.io-impl", "org.apache.iceberg.aws.s3.S3FileIO") \
        .config("spark.hadoop.fs.s3a.endpoint", "https://s3.ap-southeast-1.amazonaws.com") \
        .config("spark.hadoop.fs.s3a.access.key", os.environ.get("AWS_ACCESS_KEY_ID", "")) \
        .config("spark.hadoop.fs.s3a.secret.key", os.environ.get("AWS_SECRET_ACCESS_KEY", "")) \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .getOrCreate()


def create_indicators_table(spark: SparkSession):
    """Create momentum_indicators and indicator_history tables."""
    create_sql = """
    CREATE TABLE IF NOT EXISTS iceberg.crypto_lakehouse.momentum_indicators (
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
    """
    spark.sql(create_sql)
    logger.info("Created gold.momentum_indicators table")

    history_sql = """
    CREATE TABLE IF NOT EXISTS iceberg.crypto_lakehouse.indicator_history (
        exchange STRING NOT NULL,
        symbol STRING NOT NULL,
        interval STRING NOT NULL,
        candle_time BIGINT NOT NULL,
        candle_timestamp TIMESTAMP NOT NULL,
        close_price DOUBLE,
        volume DOUBLE,
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
        computed_at TIMESTAMP NOT NULL,
        _partition_date DATE NOT NULL
    ) USING iceberg
    PARTITIONED BY (_partition_date, interval, exchange)
    TBLPROPERTIES (
        'write.format.default' = 'parquet',
        'write.parquet.compression-codec' = 'snappy'
    )
    """
    spark.sql(history_sql)
    logger.info("Created gold.indicator_history table")


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

    # Calculate EMA (Exponential Moving Average)
    # EMA = Price * multiplier + EMA(previous) * (1 - multiplier)
    # multiplier = 2 / (period + 1)

    fast_multiplier = 2.0 / (fast + 1)
    slow_multiplier = 2.0 / (slow + 1)
    signal_multiplier = 2.0 / (signal + 1)

    # Simple approximation using weighted average
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
    logger.info("Starting technical indicators calculation")

    spark = create_spark_session()

    try:
        # Create table
        create_indicators_table(spark)

        # Read 1h klines from Silver (last 7 days for sufficient history)
        from datetime import datetime, timedelta
        date_7d_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        klines_df = spark.table("iceberg.crypto_lakehouse.kline_multi_timeframe") \
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

        logger.info("Calculating RSI...")
        df = calculate_rsi(klines_df, period=14)

        logger.info("Calculating MACD...")
        df = calculate_macd(df)

        logger.info("Calculating Bollinger Bands...")
        df = calculate_bollinger_bands(df, period=20)

        logger.info("Calculating SMAs...")
        df = calculate_sma(df, periods=[20, 50])

        history_df = df.select(
            lit("aggregated").alias("exchange"),
            col("symbol"),
            lit("1h").alias("interval"),
            col("event_time").alias("candle_time"),
            (col("event_time") / 1000).cast("timestamp").alias("candle_timestamp"),
            col("close_price"),
            col("volume"),
            col("rsi_14"),
            col("macd"),
            col("macd_signal"),
            col("macd_histogram"),
            col("bb_upper"),
            col("bb_middle"),
            col("bb_lower"),
            col("bb_width"),
            col("volume_sma_20"),
            col("price_sma_20"),
            col("price_sma_50"),
            col("ema_12").alias("price_ema_12"),
            col("ema_26").alias("price_ema_26"),
            current_timestamp().alias("computed_at"),
            to_date((col("event_time") / 1000).cast("timestamp")).alias("_partition_date"),
        )

        logger.info("Writing to gold.indicator_history...")
        history_df.writeTo("iceberg.crypto_lakehouse.indicator_history").append()

        # Get latest values per symbol
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
        result_df.write \
            .format("iceberg") \
            .mode("overwrite") \
            .option("overwrite-mode", "dynamic") \
            .saveAsTable("iceberg.crypto_lakehouse.momentum_indicators")

        count = result_df.count()
        history_count = history_df.count()
        logger.info(f"✅ Calculated indicators for {count} symbols")
        logger.info(f"✅ Wrote {history_count} indicator history rows")

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
