"""
Silver Layer - Cleaned & Unified Data
Deduplicates, validates, and unifies data from Bronze layer
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, first, sum as _sum, avg, max as _max, min as _min,
    when, lit, current_timestamp, to_date, from_unixtime,
    window, count, stddev, expr, array, struct
)
from pyspark.sql.window import Window
import logging

logger = logging.getLogger(__name__)


class SilverTickerTransformation:
    """Transform Bronze ticker to Silver unified ticker"""

    def __init__(self, spark: SparkSession):
        self.spark = spark
        self.bronze_table = "iceberg_catalog.bronze.ticker"
        self.silver_table = "iceberg_catalog.silver.ticker_unified"

    def create_table(self):
        """Create Silver ticker_unified table"""
        create_sql = """
        CREATE TABLE IF NOT EXISTS iceberg_catalog.silver.ticker_unified (
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
        """
        self.spark.sql(create_sql)

    def transform(self, batch_date: str = None):
        """
        Transform Bronze → Silver
        - Deduplicate by (symbol, event_time, exchange)
        - Validate price ranges
        - Calculate mid-price and spread
        - Quality scoring
        """
        # Read from Bronze
        bronze_df = self.spark.table(self.bronze_table)

        if batch_date:
            bronze_df = bronze_df.filter(col("_partition_date") == batch_date)

        # Deduplicate
        window_spec = Window.partitionBy("symbol", "event_time", "exchange").orderBy(col("ingestion_time").desc())
        deduped = bronze_df.withColumn("row_num", expr("row_number() OVER (PARTITION BY symbol, event_time, exchange ORDER BY ingestion_time DESC)")) \
                          .filter(col("row_num") == 1) \
                          .drop("row_num")

        # Validate price ranges (reject outliers)
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
                 (abs(col("price_binance") - col("price_okx")) / col("price_mid")) * 100)
            .otherwise(0)
        )

        # Quality score (0-100)
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
        unified.writeTo(self.silver_table).append()

        logger.info(f"Transformed {unified.count()} records to Silver ticker_unified")


class SilverKlineAggregation:
    """Aggregate Bronze klines to Silver multi-timeframe"""

    def __init__(self, spark: SparkSession):
        self.spark = spark
        self.bronze_table = "iceberg_catalog.bronze.kline"
        self.silver_table = "iceberg_catalog.silver.kline_multi_timeframe"

    def create_table(self):
        """Create Silver kline_multi_timeframe table"""
        create_sql = """
        CREATE TABLE IF NOT EXISTS iceberg_catalog.silver.kline_multi_timeframe (
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
        """
        self.spark.sql(create_sql)

    def aggregate_timeframe(self, source_interval: str, target_interval: str, multiplier: int):
        """
        Aggregate from source interval to target interval
        Example: 1m → 5m (multiplier=5)
        """
        bronze_df = self.spark.table(self.bronze_table).filter(col("interval") == source_interval)

        # Group by time windows
        aggregated = bronze_df.groupBy(
            "symbol",
            window(from_unixtime(col("event_time") / 1000), f"{multiplier} minutes").alias("time_window")
        ).agg(
            first("open_price").alias("open_price"),
            _max("high_price").alias("high_price"),
            _min("low_price").alias("low_price"),
            first(col("close_price"), ignorenulls=True).alias("close_price"),
            _sum("volume").alias("volume"),
            _sum("trade_count").alias("trade_count")
        )

        # Add metadata
        result = aggregated.select(
            (col("time_window.start").cast("long") * 1000).alias("event_time"),
            col("symbol"),
            lit(target_interval).alias("interval"),
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

        result.writeTo(self.silver_table).append()
        logger.info(f"Aggregated {result.count()} {target_interval} candles")
