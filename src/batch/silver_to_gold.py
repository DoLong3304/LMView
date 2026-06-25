"""
Silver → Gold Aggregation Pipeline
Creates business metrics and market overview from Silver layer
Runs every 5 minutes for real-time market overview
"""
import os
import sys
from pathlib import Path
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_timestamp, desc, asc, when, expr
from pyspark.sql.window import Window
import logging

# Add project src to path
PROJECT_DIR = Path(os.environ.get("CRYPTO_PROJECT_DIR", "/app"))
sys.path.insert(0, str(PROJECT_DIR / "src"))

from lakehouse.gold.aggregations import GoldMarketOverview, GoldSymbolStatistics

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def create_spark_session():
    """Create Spark session with Iceberg config"""
    return SparkSession.builder \
        .appName("Silver_to_Gold_Aggregation") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
        .config("spark.sql.catalog.iceberg_catalog", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.iceberg_catalog.type", "hadoop") \
        .config("spark.sql.catalog.iceberg_catalog.warehouse", "s3a://cryptoprice/warehouse") \
        .config("spark.sql.catalog.iceberg_catalog.io-impl", "org.apache.iceberg.aws.s3.S3FileIO") \
        .config("spark.hadoop.fs.s3a.endpoint", os.getenv("MINIO_ENDPOINT", "http://minio:9000")) \
        .config("spark.hadoop.fs.s3a.access.key", os.getenv("MINIO_ACCESS_KEY", "")) \
        .config("spark.hadoop.fs.s3a.secret.key", os.getenv("MINIO_SECRET_KEY", "")) \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider") \
        .config("spark.sql.catalog.iceberg_catalog.client.region", "us-east-1") \
        .config("spark.sql.catalog.iceberg_catalog.s3.endpoint", os.getenv("MINIO_ENDPOINT", "http://minio:9000")) \
        .config("spark.sql.catalog.iceberg_catalog.s3.access-key-id", os.getenv("MINIO_ACCESS_KEY", "")) \
        .config("spark.sql.catalog.iceberg_catalog.s3.secret-access-key", os.getenv("MINIO_SECRET_KEY", "")) \
        .getOrCreate()


def create_coin_ticker_table(spark: SparkSession):
    """Create coin_ticker table for market overview API"""
    create_sql = """
    CREATE TABLE IF NOT EXISTS iceberg.crypto_lakehouse.coin_ticker (
        symbol STRING,
        close DOUBLE,
        h24_price_change_pct DOUBLE,
        h24_volume DOUBLE,
        h24_quote_volume DOUBLE,
        market_cap DOUBLE,
        rank INT,
        last_updated TIMESTAMP
    ) USING iceberg
    """
    spark.sql(create_sql)
    logger.info("Created coin_ticker table")


def populate_coin_ticker(spark: SparkSession):
    """
    Populate coin_ticker from Silver ticker_unified
    This table is used by FastAPI market overview endpoint
    """
    logger.info("Populating coin_ticker from Silver layer...")

    # Read Silver ticker data
    silver_df = spark.table("iceberg.crypto_lakehouse.ticker_unified")

    # Get latest price per symbol
    latest_window = Window.partitionBy("symbol").orderBy(desc("event_time"))
    latest_df = silver_df.withColumn("row_num", expr("row_number() OVER (PARTITION BY symbol ORDER BY event_time DESC)")) \
                        .filter(col("row_num") == 1) \
                        .drop("row_num")

    # Calculate 24h ago timestamp
    from pyspark.sql.functions import lit
    from datetime import datetime, timedelta
    now_ms = int(datetime.now().timestamp() * 1000)
    time_24h_ago = now_ms - (24 * 60 * 60 * 1000)

    # Get price 24h ago
    price_24h_df = silver_df.filter(
        (col("event_time") >= time_24h_ago - 300000) &  # 5 min buffer
        (col("event_time") <= time_24h_ago + 300000)
    ).groupBy("symbol").agg(
        expr("avg(price_mid) as price_24h_ago")
    )

    # Calculate 24h volume
    volume_24h_df = silver_df.filter(
        col("event_time") >= time_24h_ago
    ).groupBy("symbol").agg(
        expr("sum(volume_total) as h24_volume")
    )

    # Join all data
    result_df = latest_df.select(
        col("symbol"),
        col("price_mid").alias("close")
    ).join(price_24h_df, "symbol", "left") \
     .join(volume_24h_df, "symbol", "left")

    # Calculate 24h price change percentage
    result_df = result_df.withColumn(
        "h24_price_change_pct",
        when((col("price_24h_ago").isNotNull()) & (col("price_24h_ago") > 0),
             ((col("close") - col("price_24h_ago")) / col("price_24h_ago")) * 100)
        .otherwise(0)
    )

    # Calculate quote volume (price * volume)
    result_df = result_df.withColumn(
        "h24_quote_volume",
        col("close") * col("h24_volume")
    )

    # Calculate market cap (price * volume as proxy)
    result_df = result_df.withColumn(
        "market_cap",
        col("h24_quote_volume") * 10  # Rough estimate
    )

    # Rank by quote volume
    result_df = result_df.withColumn(
        "rank",
        expr("row_number() OVER (ORDER BY h24_quote_volume DESC)")
    )

    # Add timestamp
    result_df = result_df.withColumn("last_updated", current_timestamp())

    # Select final columns
    final_df = result_df.select(
        "symbol",
        "close",
        "h24_price_change_pct",
        "h24_volume",
        "h24_quote_volume",
        "market_cap",
        "rank",
        "last_updated"
    ).filter(col("symbol").like("%USDT"))  # Only USDT pairs

    # Write to coin_ticker (overwrite)
    final_df.write \
        .format("iceberg") \
        .mode("overwrite") \
        .saveAsTable("iceberg.crypto_lakehouse.coin_ticker")

    count = final_df.count()
    logger.info(f"Populated coin_ticker with {count} symbols")

    # Show sample
    logger.info("Sample data:")
    final_df.orderBy(desc("h24_quote_volume")).show(10, False)


def main():
    """Main aggregation pipeline"""
    logger.info("Starting Silver → Gold aggregation pipeline")

    spark = create_spark_session()

    try:
        # Create Gold tables
        logger.info("Creating Gold tables...")
        market_overview = GoldMarketOverview(spark)
        market_overview.create_table()

        # Create coin_ticker table for API
        create_coin_ticker_table(spark)

        # Populate coin_ticker from Silver
        populate_coin_ticker(spark)

        # Calculate market overview metrics
        logger.info("Calculating market overview...")
        market_overview.calculate()

        logger.info("Silver → Gold aggregation completed successfully")

    except Exception as e:
        logger.error(f"Silver → Gold aggregation failed: {e}", exc_info=True)
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
