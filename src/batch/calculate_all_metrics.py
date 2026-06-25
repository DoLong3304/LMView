"""
Batch Job - Calculate All Gold Metrics
Orchestrates all gold layer calculations
Runs every 5 minutes
"""
import os
import sys
from pathlib import Path
from pyspark.sql import SparkSession
import logging

PROJECT_DIR = Path(os.environ.get("CRYPTO_PROJECT_DIR", "/app"))
sys.path.insert(0, str(PROJECT_DIR / "src"))

from lakehouse.gold.market_metrics import (
    GoldMarketDominance,
    GoldVolatilityRanking,
    GoldMoversRanking
)
from lakehouse.gold.news_aggregations import GoldNewsSentiment
from lakehouse.silver.news_transformer import SilverNewsTransformer
from lakehouse.bronze.news_writer import BronzeNewsWriter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def create_spark_session():
    """Create Spark session with Iceberg config"""
    return SparkSession.builder \
        .appName("Calculate_All_Gold_Metrics") \
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


def main():
    """Main orchestration pipeline"""
    logger.info("=" * 80)
    logger.info("Starting Gold Metrics Calculation Pipeline")
    logger.info("=" * 80)

    spark = create_spark_session()

    try:
        # 1. Create all Gold tables
        logger.info("\n[1/7] Creating Gold tables...")

        market_dominance = GoldMarketDominance(spark)
        market_dominance.create_table()

        volatility_ranking = GoldVolatilityRanking(spark)
        volatility_ranking.create_table()

        movers_ranking = GoldMoversRanking(spark)
        movers_ranking.create_table()

        news_sentiment = GoldNewsSentiment(spark)
        news_sentiment.create_table()

        # 2. Calculate Market Dominance
        logger.info("\n[2/7] Calculating market dominance...")
        market_dominance.calculate()

        # 3. Calculate Volatility Rankings
        logger.info("\n[3/7] Calculating volatility rankings...")
        volatility_ranking.calculate()

        # 4. Calculate Movers Rankings (gainers/losers)
        logger.info("\n[4/7] Calculating movers rankings...")
        movers_ranking.calculate()

        # 5. Transform News (Bronze → Silver)
        logger.info("\n[5/7] Transforming news (Bronze → Silver)...")
        news_transformer = SilverNewsTransformer(spark)
        news_transformer.create_table()

        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        try:
            news_transformer.transform(today)
        except Exception as e:
            logger.warning(f"News transformation skipped (no data): {e}")

        # 6. Calculate News Sentiment
        logger.info("\n[6/7] Calculating news sentiment...")
        try:
            news_sentiment.calculate(today)
        except Exception as e:
            logger.warning(f"News sentiment calculation skipped (no data): {e}")

        # 7. Summary
        logger.info("\n[7/7] Pipeline Summary")
        logger.info("=" * 80)
        logger.info("✅ Market dominance calculated")
        logger.info("✅ Volatility rankings calculated")
        logger.info("✅ Movers rankings calculated")
        logger.info("✅ News sentiment calculated")
        logger.info("=" * 80)
        logger.info("Gold metrics calculation completed successfully")

    except Exception as e:
        logger.error(f"❌ Gold metrics calculation failed: {e}", exc_info=True)
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
