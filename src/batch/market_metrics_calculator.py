"""
Market Metrics Calculator - Spark Job
Calculates price changes, top gainers/losers, market statistics
Runs every 5 minutes
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, lag, when, round as spark_round, desc, asc,
    sum as _sum, avg, count, max as _max, min as _min,
    current_timestamp, window, from_unixtime, unix_timestamp
)
from pyspark.sql.window import Window
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MarketMetricsCalculator:
    """
    Calculate real-time market metrics from Silver layer
    - Price changes (1h, 24h, 7d)
    - Top gainers/losers
    - Market statistics
    - Volume analysis
    """

    def __init__(self, spark: SparkSession):
        self.spark = spark
        self.silver_ticker_table = "iceberg_catalog.silver.ticker_unified"
        self.output_table = "iceberg_catalog.gold.market_metrics_realtime"

    def create_output_table(self):
        """Create output table for market metrics"""
        create_sql = """
        CREATE TABLE IF NOT EXISTS iceberg_catalog.gold.market_metrics_realtime (
            symbol STRING,
            current_price DOUBLE,
            price_1h_ago DOUBLE,
            price_24h_ago DOUBLE,
            price_7d_ago DOUBLE,
            change_1h_pct DOUBLE,
            change_24h_pct DOUBLE,
            change_7d_pct DOUBLE,
            volume_24h DOUBLE,
            high_24h DOUBLE,
            low_24h DOUBLE,
            market_cap DOUBLE,
            rank INT,
            last_updated TIMESTAMP
        ) USING iceberg
        """
        self.spark.sql(create_sql)
        logger.info("Created market_metrics_realtime table")

    def calculate_metrics(self):
        """
        Calculate all market metrics
        Returns DataFrame with metrics for all symbols
        """
        # Read from Silver ticker_unified
        ticker_df = self.spark.table(self.silver_ticker_table)

        # Get latest data per symbol
        latest_window = Window.partitionBy("symbol").orderBy(desc("event_time"))
        latest_df = ticker_df.withColumn("row_num",
                                        expr("row_number() OVER (PARTITION BY symbol ORDER BY event_time DESC)")) \
                            .filter(col("row_num") == 1) \
                            .drop("row_num")

        # Calculate time windows
        now_ms = int(datetime.now().timestamp() * 1000)
        time_1h_ago = now_ms - (1 * 60 * 60 * 1000)
        time_24h_ago = now_ms - (24 * 60 * 60 * 1000)
        time_7d_ago = now_ms - (7 * 24 * 60 * 60 * 1000)

        # Get historical prices
        historical_df = ticker_df.select(
            col("symbol"),
            col("event_time"),
            col("price_mid").alias("historical_price")
        )

        # Join with historical data for 1h ago
        price_1h = historical_df.filter(
            (col("event_time") >= time_1h_ago - 300000) &  # 5 min buffer
            (col("event_time") <= time_1h_ago + 300000)
        ).groupBy("symbol").agg(
            avg("historical_price").alias("price_1h_ago")
        )

        # Join with historical data for 24h ago
        price_24h = historical_df.filter(
            (col("event_time") >= time_24h_ago - 300000) &
            (col("event_time") <= time_24h_ago + 300000)
        ).groupBy("symbol").agg(
            avg("historical_price").alias("price_24h_ago")
        )

        # Join with historical data for 7d ago
        price_7d = historical_df.filter(
            (col("event_time") >= time_7d_ago - 3600000) &  # 1 hour buffer
            (col("event_time") <= time_7d_ago + 3600000)
        ).groupBy("symbol").agg(
            avg("historical_price").alias("price_7d_ago")
        )

        # Calculate 24h high/low and volume
        stats_24h = ticker_df.filter(
            col("event_time") >= time_24h_ago
        ).groupBy("symbol").agg(
            _max("price_mid").alias("high_24h"),
            _min("price_mid").alias("low_24h"),
            _sum("volume_total").alias("volume_24h")
        )

        # Join all data
        metrics_df = latest_df.select(
            col("symbol"),
            col("price_mid").alias("current_price")
        )

        metrics_df = metrics_df.join(price_1h, "symbol", "left") \
                              .join(price_24h, "symbol", "left") \
                              .join(price_7d, "symbol", "left") \
                              .join(stats_24h, "symbol", "left")

        # Calculate percentage changes
        metrics_df = metrics_df.withColumn(
            "change_1h_pct",
            when(col("price_1h_ago").isNotNull() & (col("price_1h_ago") > 0),
                 ((col("current_price") - col("price_1h_ago")) / col("price_1h_ago")) * 100)
            .otherwise(0)
        ).withColumn(
            "change_24h_pct",
            when(col("price_24h_ago").isNotNull() & (col("price_24h_ago") > 0),
                 ((col("current_price") - col("price_24h_ago")) / col("price_24h_ago")) * 100)
            .otherwise(0)
        ).withColumn(
            "change_7d_pct",
            when(col("price_7d_ago").isNotNull() & (col("price_7d_ago") > 0),
                 ((col("current_price") - col("price_7d_ago")) / col("price_7d_ago")) * 100)
            .otherwise(0)
        )

        # Calculate market cap (price * volume as proxy)
        metrics_df = metrics_df.withColumn(
            "market_cap",
            col("current_price") * col("volume_24h")
        )

        # Rank by market cap
        rank_window = Window.orderBy(desc("market_cap"))
        metrics_df = metrics_df.withColumn("rank", expr("row_number() OVER (ORDER BY market_cap DESC)"))

        # Round values
        metrics_df = metrics_df.withColumn("current_price", spark_round(col("current_price"), 8)) \
                              .withColumn("change_1h_pct", spark_round(col("change_1h_pct"), 2)) \
                              .withColumn("change_24h_pct", spark_round(col("change_24h_pct"), 2)) \
                              .withColumn("change_7d_pct", spark_round(col("change_7d_pct"), 2)) \
                              .withColumn("volume_24h", spark_round(col("volume_24h"), 2)) \
                              .withColumn("high_24h", spark_round(col("high_24h"), 8)) \
                              .withColumn("low_24h", spark_round(col("low_24h"), 8)) \
                              .withColumn("market_cap", spark_round(col("market_cap"), 2))

        # Add timestamp
        metrics_df = metrics_df.withColumn("last_updated", current_timestamp())

        logger.info(f"Calculated metrics for {metrics_df.count()} symbols")
        return metrics_df

    def get_top_gainers(self, metrics_df, limit: int = 10):
        """Get top gainers by 24h change"""
        return metrics_df.orderBy(desc("change_24h_pct")).limit(limit)

    def get_top_losers(self, metrics_df, limit: int = 10):
        """Get top losers by 24h change"""
        return metrics_df.orderBy(asc("change_24h_pct")).limit(limit)

    def get_market_summary(self, metrics_df):
        """Calculate overall market summary"""
        summary = metrics_df.agg(
            count("symbol").alias("total_symbols"),
            _sum("volume_24h").alias("total_volume_24h"),
            _sum("market_cap").alias("total_market_cap"),
            avg("change_24h_pct").alias("avg_change_24h_pct"),
            count(when(col("change_24h_pct") > 0, 1)).alias("gainers_count"),
            count(when(col("change_24h_pct") < 0, 1)).alias("losers_count")
        ).collect()[0]

        return {
            "total_symbols": summary["total_symbols"],
            "total_volume_24h": round(summary["total_volume_24h"], 2),
            "total_market_cap": round(summary["total_market_cap"], 2),
            "avg_change_24h_pct": round(summary["avg_change_24h_pct"], 2),
            "gainers_count": summary["gainers_count"],
            "losers_count": summary["losers_count"],
            "neutral_count": summary["total_symbols"] - summary["gainers_count"] - summary["losers_count"]
        }

    def save_to_table(self, metrics_df):
        """Save metrics to Iceberg table"""
        # Overwrite with latest data
        metrics_df.writeTo(self.output_table).overwritePartitions()
        logger.info(f"Saved {metrics_df.count()} records to {self.output_table}")

    def save_to_redis(self, metrics_df):
        """Save metrics to Redis for fast API access"""
        # Convert to JSON and save to Redis
        metrics_json = metrics_df.toJSON().collect()

        # This will be implemented with Redis connection
        # For now, just log
        logger.info(f"Would save {len(metrics_json)} records to Redis")

    def run(self):
        """Run the complete metrics calculation pipeline"""
        try:
            logger.info("Starting market metrics calculation...")

            # Create table if not exists
            self.create_output_table()

            # Calculate metrics
            metrics_df = self.calculate_metrics()

            # Get top gainers/losers
            top_gainers = self.get_top_gainers(metrics_df, 10)
            top_losers = self.get_top_losers(metrics_df, 10)

            logger.info("Top 10 Gainers:")
            top_gainers.select("symbol", "current_price", "change_24h_pct").show(10, False)

            logger.info("Top 10 Losers:")
            top_losers.select("symbol", "current_price", "change_24h_pct").show(10, False)

            # Get market summary
            summary = self.get_market_summary(metrics_df)
            logger.info(f"Market Summary: {summary}")

            # Save to table
            self.save_to_table(metrics_df)

            # Save to Redis (for fast API access)
            self.save_to_redis(metrics_df)

            logger.info("Market metrics calculation completed successfully")

        except Exception as e:
            logger.error(f"Error calculating market metrics: {e}")
            raise


def main():
    """Main entry point"""
    # Create Spark session
    spark = SparkSession.builder \
        .appName("Market_Metrics_Calculator") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
        .config("spark.sql.catalog.iceberg_catalog", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.iceberg_catalog.type", "hadoop") \
        .config("spark.sql.catalog.iceberg_catalog.warehouse", "s3a://lakehouse/warehouse") \
        .getOrCreate()

    # Run calculator
    calculator = MarketMetricsCalculator(spark)
    calculator.run()

    spark.stop()


if __name__ == "__main__":
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    main()
