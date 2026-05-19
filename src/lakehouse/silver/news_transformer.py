"""
Silver Layer - News Transformer
Deduplicate, enrich, and clean news articles from Bronze
"""
import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, row_number, desc, when, size, array_distinct,
    current_timestamp, to_date, expr, lit
)
from pyspark.sql.window import Window
from pyspark.sql.types import (
    StructType, StructField, StringType, LongType,
    DoubleType, ArrayType, TimestampType, DateType, IntegerType
)

logger = logging.getLogger(__name__)


class SilverNewsTransformer:
    """Transform Bronze news to Silver layer"""

    def __init__(self, spark: SparkSession):
        self.spark = spark
        self.bronze_table = "iceberg_catalog.bronze.news"
        self.silver_table = "iceberg_catalog.silver.news_enriched"

    def create_table(self):
        """Create Silver news_enriched table"""
        create_sql = """
        CREATE TABLE IF NOT EXISTS iceberg_catalog.silver.news_enriched (
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
        TBLPROPERTIES (
            'write.format.default' = 'parquet',
            'write.parquet.compression-codec' = 'snappy'
        )
        """
        self.spark.sql(create_sql)
        logger.info("Created silver.news_enriched table")

    def transform(self, partition_date: str = None):
        """
        Transform Bronze news to Silver

        Args:
            partition_date: Optional date filter (YYYY-MM-DD)
        """
        # Read Bronze
        bronze_df = self.spark.table(self.bronze_table)

        if partition_date:
            bronze_df = bronze_df.filter(col("_partition_date") == partition_date)

        # Deduplicate by URL (keep latest)
        window = Window.partitionBy("url").orderBy(desc("ingestion_time"))
        deduped_df = bronze_df \
            .withColumn("row_num", row_number().over(window)) \
            .filter(col("row_num") == 1) \
            .drop("row_num")

        # Calculate impact score
        # Impact = |sentiment| * source_credibility * symbol_count
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

        # Build CASE WHEN for source credibility
        credibility_expr = "CASE "
        for source, cred in source_credibility.items():
            credibility_expr += f"WHEN source = '{source}' THEN {cred} "
        credibility_expr += "ELSE 0.5 END"

        enriched_df = deduped_df.select(
            col("id"),
            col("event_time").alias("published_at"),
            col("source"),
            col("title"),
            col("summary"),
            col("url"),
            array_distinct(col("symbols")).alias("symbols"),
            col("sentiment_score"),
            col("sentiment_label"),
            # Impact score
            (
                expr("ABS(COALESCE(sentiment_score, 0))") *
                expr(credibility_expr) *
                expr("COALESCE(SIZE(symbols), 1)")
            ).alias("impact_score"),
            # Quality score (0-100)
            when(
                (col("title").isNotNull()) &
                (col("summary").isNotNull()) &
                (size(col("symbols")) > 0) &
                (col("sentiment_score").isNotNull()),
                100
            ).when(
                (col("title").isNotNull()) &
                (col("summary").isNotNull()),
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

        # Write to Silver (overwrite partition)
        if partition_date:
            filtered_df.write \
                .format("iceberg") \
                .mode("overwrite") \
                .option("overwrite-mode", "dynamic") \
                .saveAsTable(self.silver_table)
        else:
            filtered_df.writeTo(self.silver_table).append()

        count = filtered_df.count()
        logger.info(f"Transformed {count} articles to silver.news_enriched")
        return count
