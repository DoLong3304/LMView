"""
Gold Layer - Business Metrics & Analytics
Pre-aggregated metrics for dashboards and analytics
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, sum as _sum, avg, max as _max, min as _min, count,
    current_timestamp, to_date, from_unixtime, lag, desc, asc,
    stddev, collect_list, struct, lit, when, expr
)
from pyspark.sql.window import Window
import logging

logger = logging.getLogger(__name__)


class GoldMarketOverview:
    """Calculate market overview metrics"""

    def __init__(self, spark: SparkSession):
        self.spark = spark
        self.silver_table = "iceberg.crypto_lakehouse.silver_ticker_unified"
        self.gold_table = "iceberg.crypto_lakehouse.gold_market_overview"

    def create_table(self):
        """Create Gold market_overview table"""
        create_sql = """
        CREATE TABLE IF NOT EXISTS iceberg.crypto_lakehouse.gold_market_overview (
            snapshot_time TIMESTAMP,
            total_symbols INT,
            total_volume_24h DOUBLE,
            avg_spread_pct DOUBLE,
            top_10_gainers ARRAY<STRUCT<symbol:STRING, change_pct:DOUBLE, price:DOUBLE>>,
            top_10_losers ARRAY<STRUCT<symbol:STRING, change_pct:DOUBLE, price:DOUBLE>>,
            market_cap_total DOUBLE,
            _partition_date DATE
        ) USING iceberg
        PARTITIONED BY (_partition_date)
        """
        self.spark.sql(create_sql)

    def calculate(self):
        """Calculate market overview metrics"""
        silver_df = self.spark.table(self.silver_table)

        # Calculate 24h change
        window_24h = Window.partitionBy("symbol").orderBy("event_time").rangeBetween(-86400000, 0)

        metrics = silver_df.withColumn(
            "price_24h_ago",
            lag("price_mid", 1).over(window_24h)
        ).withColumn(
            "change_pct_24h",
            when(col("price_24h_ago").isNotNull() & (col("price_24h_ago") > 0),
                 ((col("price_mid") - col("price_24h_ago")) / col("price_24h_ago")) * 100)
            .otherwise(0)
        )

        # Get latest snapshot
        latest_window = Window.partitionBy("symbol").orderBy(desc("event_time"))
        latest_metrics = metrics.withColumn("row_num", expr("row_number() OVER (PARTITION BY symbol ORDER BY event_time DESC)")) \
                               .filter(col("row_num") == 1) \
                               .drop("row_num")

        # Top 10 gainers
        top_gainers = latest_metrics.orderBy(desc("change_pct_24h")).limit(10) \
                                    .select(
                                        struct(
                                            col("symbol"),
                                            col("change_pct_24h").alias("change_pct"),
                                            col("price_mid").alias("price")
                                        ).alias("gainer")
                                    ) \
                                    .agg(collect_list("gainer").alias("top_10_gainers"))

        # Top 10 losers
        top_losers = latest_metrics.orderBy(asc("change_pct_24h")).limit(10) \
                                   .select(
                                       struct(
                                           col("symbol"),
                                           col("change_pct_24h").alias("change_pct"),
                                           col("price_mid").alias("price")
                                       ).alias("loser")
                                   ) \
                                   .agg(collect_list("loser").alias("top_10_losers"))

        # Aggregate metrics
        overview = latest_metrics.agg(
            count("symbol").alias("total_symbols"),
            _sum("volume_total").alias("total_volume_24h"),
            avg("spread_pct").alias("avg_spread_pct"),
            _sum(col("price_mid") * col("volume_total")).alias("market_cap_total")
        )

        # Combine all metrics
        result = overview.crossJoin(top_gainers).crossJoin(top_losers) \
                        .withColumn("snapshot_time", current_timestamp()) \
                        .withColumn("_partition_date", to_date(current_timestamp()))

        result.writeTo(self.gold_table).append()
        logger.info("Calculated market overview metrics")


class GoldSymbolStatistics:
    """Calculate per-symbol daily statistics"""

    def __init__(self, spark: SparkSession):
        self.spark = spark
        self.silver_kline_table = "iceberg.crypto_lakehouse.silver_kline_multi_timeframe"
        self.silver_ticker_table = "iceberg.crypto_lakehouse.silver_ticker_unified"
        self.gold_table = "iceberg.crypto_lakehouse.gold_symbol_stats_daily"

    def create_table(self):
        """Create Gold symbol_stats_daily table"""
        create_sql = """
        CREATE TABLE IF NOT EXISTS iceberg.crypto_lakehouse.gold_symbol_stats_daily (
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
        """
        self.spark.sql(create_sql)

    def calculate(self, date: str):
        """Calculate daily statistics for all symbols"""
        # Get 1d candles
        kline_df = self.spark.table(self.silver_kline_table) \
                            .filter((col("interval") == "1d") & (col("_partition_date") == date))

        # Get ticker data for spread
        ticker_df = self.spark.table(self.silver_ticker_table) \
                             .filter(col("_partition_date") == date)

        # Calculate volatility (standard deviation of prices)
        volatility = ticker_df.groupBy("symbol").agg(
            stddev("price_mid").alias("volatility"),
            avg("spread_pct").alias("avg_spread_pct")
        )

        # Join kline with volatility
        stats = kline_df.join(volatility, "symbol", "left")

        # Calculate additional metrics
        result = stats.select(
            col("symbol"),
            lit(date).cast("date").alias("date"),
            col("open_price"),
            col("high_price"),
            col("low_price"),
            col("close_price"),
            col("volume"),
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

        result.writeTo(self.gold_table).append()
        logger.info(f"Calculated daily statistics for {result.count()} symbols")


class GoldSectorPerformance:
    """Calculate sector-level performance (if symbols are categorized)"""

    def __init__(self, spark: SparkSession):
        self.spark = spark
        self.silver_table = "iceberg.crypto_lakehouse.silver_ticker_unified"
        self.gold_table = "iceberg.crypto_lakehouse.gold_sector_performance"

    def create_table(self):
        """Create Gold sector_performance table"""
        create_sql = """
        CREATE TABLE IF NOT EXISTS iceberg.crypto_lakehouse.gold_sector_performance (
            sector STRING,
            snapshot_time TIMESTAMP,
            avg_change_pct DOUBLE,
            total_volume DOUBLE,
            symbol_count INT,
            top_symbol STRING,
            top_symbol_change_pct DOUBLE,
            _partition_date DATE
        ) USING iceberg
        PARTITIONED BY (_partition_date)
        """
        self.spark.sql(create_sql)

    def calculate(self):
        """
        Calculate sector performance
        Note: Requires symbol-to-sector mapping
        For now, categorize by market cap tiers
        """
        silver_df = self.spark.table(self.silver_table)

        # Calculate 24h change
        window_24h = Window.partitionBy("symbol").orderBy("event_time").rangeBetween(-86400000, 0)

        metrics = silver_df.withColumn(
            "price_24h_ago",
            lag("price_mid", 1).over(window_24h)
        ).withColumn(
            "change_pct_24h",
            when(col("price_24h_ago").isNotNull() & (col("price_24h_ago") > 0),
                 ((col("price_mid") - col("price_24h_ago")) / col("price_24h_ago")) * 100)
            .otherwise(0)
        )

        # Categorize by volume (proxy for market cap)
        categorized = metrics.withColumn(
            "sector",
            when(col("volume_total") > 1000000, "Large Cap")
            .when(col("volume_total") > 100000, "Mid Cap")
            .otherwise("Small Cap")
        )

        # Get latest snapshot
        latest_window = Window.partitionBy("symbol").orderBy(desc("event_time"))
        latest = categorized.withColumn("row_num", expr("row_number() OVER (PARTITION BY symbol ORDER BY event_time DESC)")) \
                           .filter(col("row_num") == 1) \
                           .drop("row_num")

        # Aggregate by sector
        sector_stats = latest.groupBy("sector").agg(
            avg("change_pct_24h").alias("avg_change_pct"),
            _sum("volume_total").alias("total_volume"),
            count("symbol").alias("symbol_count")
        )

        # Get top symbol per sector
        top_symbols_window = Window.partitionBy("sector").orderBy(desc("change_pct_24h"))
        top_symbols = latest.withColumn("rank", expr("row_number() OVER (PARTITION BY sector ORDER BY change_pct_24h DESC)")) \
                           .filter(col("rank") == 1) \
                           .select(
                               col("sector"),
                               col("symbol").alias("top_symbol"),
                               col("change_pct_24h").alias("top_symbol_change_pct")
                           )

        # Join
        result = sector_stats.join(top_symbols, "sector") \
                            .withColumn("snapshot_time", current_timestamp()) \
                            .withColumn("_partition_date", to_date(current_timestamp()))

        result.writeTo(self.gold_table).append()
        logger.info("Calculated sector performance metrics")
