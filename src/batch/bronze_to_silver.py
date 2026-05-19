"""
Bronze → Silver ETL Pipeline
Cleans, deduplicates, and unifies raw data from Bronze layer
Runs hourly to process new data
"""
import os
import sys
from pathlib import Path
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_date, date_sub
import logging

# Add project src to path
PROJECT_DIR = Path(os.environ.get("CRYPTO_PROJECT_DIR", "/app"))
sys.path.insert(0, str(PROJECT_DIR / "src"))

from lakehouse.silver.transformations import SilverTickerTransformation, SilverKlineAggregation

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def create_spark_session():
    """Create Spark session with Iceberg config"""
    return SparkSession.builder \
        .appName("Bronze_to_Silver_ETL") \
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


def main():
    """Main ETL pipeline"""
    logger.info("Starting Bronze → Silver ETL pipeline")

    spark = create_spark_session()

    try:
        # Create Silver tables if not exist
        logger.info("Creating Silver tables...")
        ticker_transform = SilverTickerTransformation(spark)
        ticker_transform.create_table()

        kline_transform = SilverKlineAggregation(spark)
        kline_transform.create_table()

        # Process last 2 days of data (to handle late arrivals)
        logger.info("Processing ticker data...")
        ticker_transform.transform()

        # Aggregate klines to multiple timeframes
        logger.info("Aggregating klines to 5m...")
        kline_transform.aggregate_timeframe("1m", "5m", 5)

        logger.info("Aggregating klines to 15m...")
        kline_transform.aggregate_timeframe("1m", "15m", 15)

        logger.info("Aggregating klines to 1h...")
        kline_transform.aggregate_timeframe("1m", "1h", 60)

        logger.info("Aggregating klines to 4h...")
        kline_transform.aggregate_timeframe("1h", "4h", 4)

        logger.info("Aggregating klines to 1d...")
        kline_transform.aggregate_timeframe("1h", "1d", 24)

        logger.info("Bronze → Silver ETL completed successfully")

    except Exception as e:
        logger.error(f"Bronze → Silver ETL failed: {e}", exc_info=True)
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
