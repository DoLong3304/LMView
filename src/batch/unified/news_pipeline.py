"""
Unified News Pipeline
Consolidates Bronze → Silver → Gold news transformations
Single job for entire news pipeline
"""
import os
import sys
from pathlib import Path
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, row_number, desc, when, size, array_distinct, explode,
    current_timestamp, to_date, expr, lit, count, avg, sum as _sum,
    collect_list, struct
)
from pyspark.sql.window import Window
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
        .appName("Unified_News_Pipeline") \
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


def create_tables(spark: SparkSession):
    """Create Silver and Gold news tables"""

    # Silver news_enriched
    spark.sql("""
        CREATE TABLE IF NOT EXISTS iceberg.crypto_lakehouse.news_enriched (
            id STRING NOT NULL,
            published_at BIGINT NOT NULL,
            source STRING NOT NULL,
            title STRING NOT NULL,
            summary STRING,
            url STRING NOT NULL,
            symbols ARRAY<STRING>,
            sentiment_score DOUBLE,
            sentiment_label STRING,
            impact_score DOUBLE,
            quality_score INT,
            last_updated TIMESTAMP NOT NULL,
            _partition_date DATE NOT NULL
        ) USING iceberg
        PARTITIONED BY (_partition_date)
    """)

    # Gold news_sentiment_daily
    spark.sql("""
        CREATE TABLE IF NOT EXISTS iceberg.crypto_lakehouse.news_sentiment_daily (
            symbol STRING NOT NULL,
            date DATE NOT NULL,
            article_count INT NOT NULL,
            avg_sentiment DOUBLE,
            sentiment_positive INT,
            sentiment_neutral INT,
            sentiment_negative INT,
            avg_impact_score DOUBLE,
            top_sources ARRAY<STRING>,
            trending_tags ARRAY<STRING>,
            top_headlines ARRAY<STRUCT<title:STRING, sentiment:DOUBLE, url:STRING>>
        ) USING iceberg
        PARTITIONED BY (date)
    """)

    logger.info("Created Silver and Gold news tables")


def transform_bronze_to_silver(spark: SparkSession, partition_date: str = None):
    """Transform Bronze news → Silver news_enriched"""
    logger.info("Transforming Bronze → Silver news...")

    # Read Bronze
    bronze_df = spark.table("iceberg.crypto_lakehouse.news")

    if partition_date:
        bronze_df = bronze_df.filter(col("_partition_date") == partition_date)

    # Deduplicate by URL
    window = Window.partitionBy("url").orderBy(desc("ingestion_time"))
    deduped_df = bronze_df \
        .withColumn("row_num", row_number().over(window)) \
        .filter(col("row_num") == 1) \
        .drop("row_num")

    # Source credibility mapping
    source_credibility = {
        "CoinDesk": 1.0,
        "CoinTelegraph": 0.9,
        "The Block": 0.95,
        "Decrypt": 0.85,
        "CryptoPanic": 0.8,
        "Bitcoin Magazine": 0.85,
        "CryptoSlate": 0.75,
        "BeInCrypto": 0.7,
        "NewsBTC": 0.7,
        "U.Today": 0.65,
        "Bitcoinist": 0.65,
        "CryptoNews": 0.6,
    }

    # Build CASE WHEN for credibility
    credibility_expr = "CASE "
    for source, cred in source_credibility.items():
        credibility_expr += f"WHEN source = '{source}' THEN {cred} "
    credibility_expr += "ELSE 0.5 END"

    # Enrich data
    enriched_df = deduped_df.select(
        col("url").alias("id"),  # Use URL as ID
        col("event_time").alias("published_at"),
        col("source"),
        col("title"),
        col("content").alias("summary"),
        col("url"),
        array_distinct(col("symbols")).alias("symbols"),
        col("sentiment_score"),
        when(col("sentiment_score") > 0.05, "positive")
        .when(col("sentiment_score") < -0.05, "negative")
        .otherwise("neutral").alias("sentiment_label"),
        # Impact score = |sentiment| × credibility × symbol_count
        (
            expr("ABS(COALESCE(sentiment_score, 0))") *
            expr(credibility_expr) *
            expr("COALESCE(SIZE(symbols), 1)")
        ).alias("impact_score"),
        # Quality score
        when(
            (col("title").isNotNull()) &
            (col("content").isNotNull()) &
            (size(col("symbols")) > 0) &
            (col("sentiment_score").isNotNull()),
            100
        ).when(
            (col("title").isNotNull()) &
            (col("content").isNotNull()),
            75
        ).when(
            col("title").isNotNull(),
            50
        ).otherwise(25).alias("quality_score"),
        current_timestamp().alias("last_updated"),
        col("_partition_date")
    )

    # Filter low quality
    filtered_df = enriched_df.filter(col("quality_score") >= 50)

    # Write to Silver
    if partition_date:
        filtered_df.write \
            .format("iceberg") \
            .mode("overwrite") \
            .option("overwrite-mode", "dynamic") \
            .saveAsTable("iceberg.crypto_lakehouse.news_enriched")
    else:
        filtered_df.writeTo("iceberg.crypto_lakehouse.news_enriched").append()

    count = filtered_df.count()
    logger.info(f"Transformed {count} articles to Silver")
    return count


def calculate_gold_sentiment(spark: SparkSession, date: str = None):
    """Calculate Gold news_sentiment_daily"""
    logger.info("Calculating Gold news sentiment...")

    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    # Read Silver news
    silver_df = spark.table("iceberg.crypto_lakehouse.news_enriched") \
        .filter(col("_partition_date") == date)

    # Explode symbols array
    exploded_df = silver_df.select(
        explode(col("symbols")).alias("symbol"),
        col("source"),
        col("title"),
        col("url"),
        col("sentiment_score"),
        col("sentiment_label"),
        col("impact_score"),
        col("_partition_date")
    )

    # Calculate sentiment distribution
    sentiment_stats = exploded_df.groupBy("symbol").agg(
        count("*").alias("article_count"),
        avg("sentiment_score").alias("avg_sentiment"),
        _sum(when(col("sentiment_score") > 0.05, 1).otherwise(0)).alias("sentiment_positive"),
        _sum(when((col("sentiment_score") >= -0.05) & (col("sentiment_score") <= 0.05), 1).otherwise(0)).alias("sentiment_neutral"),
        _sum(when(col("sentiment_score") < -0.05, 1).otherwise(0)).alias("sentiment_negative"),
        avg("impact_score").alias("avg_impact_score")
    )

    # Get top sources per symbol
    top_sources_df = exploded_df.groupBy("symbol", "source").agg(
        count("*").alias("source_count")
    ).withColumn("rank", row_number().over(Window.partitionBy("symbol").orderBy(desc("source_count")))) \
     .filter(col("rank") <= 5) \
     .groupBy("symbol").agg(
         collect_list("source").alias("top_sources")
     )

    # Get top headlines per symbol
    top_headlines_df = exploded_df.withColumn(
        "rank", row_number().over(Window.partitionBy("symbol").orderBy(desc("impact_score")))
    ).filter(col("rank") <= 3) \
     .groupBy("symbol").agg(
         collect_list(
             struct(
                 col("title"),
                 col("sentiment_score").alias("sentiment"),
                 col("url")
             )
         ).alias("top_headlines")
     )

    # Combine all metrics
    result = sentiment_stats \
        .join(top_sources_df, "symbol", "left") \
        .join(top_headlines_df, "symbol", "left") \
        .withColumn("date", lit(date).cast("date")) \
        .withColumn("trending_tags", array_distinct(collect_list(lit("")))) \
        .select(
            "symbol",
            "date",
            "article_count",
            "avg_sentiment",
            "sentiment_positive",
            "sentiment_neutral",
            "sentiment_negative",
            "avg_impact_score",
            "top_sources",
            "trending_tags",
            "top_headlines"
        )

    # Write to Gold
    result.write \
        .format("iceberg") \
        .mode("overwrite") \
        .option("overwrite-mode", "dynamic") \
        .saveAsTable("iceberg.crypto_lakehouse.news_sentiment_daily")

    count = result.count()
    logger.info(f"Calculated sentiment for {count} symbols")
    return count


def main():
    """Main news pipeline"""
    logger.info("=" * 80)
    logger.info("Starting Unified News Pipeline")
    logger.info("=" * 80)

    spark = create_spark_session()

    try:
        # Create tables
        create_tables(spark)

        # Get today's date
        today = datetime.now().strftime("%Y-%m-%d")

        # Transform Bronze → Silver
        silver_count = transform_bronze_to_silver(spark, partition_date=today)

        # Calculate Gold sentiment
        gold_count = calculate_gold_sentiment(spark, date=today)

        # Summary
        logger.info("=" * 80)
        logger.info("Unified News Pipeline completed successfully")
        logger.info(f"  Silver articles: {silver_count}")
        logger.info(f"  Gold symbols: {gold_count}")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"News pipeline failed: {e}", exc_info=True)
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
