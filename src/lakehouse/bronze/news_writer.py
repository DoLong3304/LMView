"""
Bronze Layer - News Writer
Writes raw news articles to Iceberg bronze.news table
"""
import logging
from datetime import datetime
from typing import List, Dict, Any
from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType, StructField, StringType, LongType,
    DoubleType, ArrayType, TimestampType, DateType
)

logger = logging.getLogger(__name__)


class BronzeNewsWriter:
    """Write raw news articles to Bronze layer"""

    def __init__(self, spark: SparkSession):
        self.spark = spark
        self.table_name = "iceberg_catalog.bronze.news"
        self.schema = self._get_schema()

    def _get_schema(self) -> StructType:
        """Define Bronze news schema"""
        return StructType([
            StructField("id", StringType(), False),
            StructField("event_time", LongType(), False),
            StructField("source", StringType(), False),
            StructField("title", StringType(), False),
            StructField("summary", StringType(), True),
            StructField("content", StringType(), True),
            StructField("url", StringType(), False),
            StructField("author", StringType(), True),
            StructField("symbols", ArrayType(StringType()), True),
            StructField("tags", ArrayType(StringType()), True),
            StructField("sentiment_score", DoubleType(), True),
            StructField("sentiment_label", StringType(), True),
            StructField("language", StringType(), True),
            StructField("region", StringType(), True),
            StructField("raw_payload", StringType(), True),
            StructField("ingestion_time", TimestampType(), False),
            StructField("_partition_date", DateType(), False),
        ])

    def create_table(self):
        """Create Bronze news table if not exists"""
        create_sql = """
        CREATE TABLE IF NOT EXISTS iceberg_catalog.bronze.news (
            id STRING NOT NULL,
            event_time BIGINT NOT NULL,
            source STRING NOT NULL,
            title STRING NOT NULL,
            summary STRING,
            content STRING,
            url STRING NOT NULL,
            author STRING,
            symbols ARRAY<STRING>,
            tags ARRAY<STRING>,
            sentiment_score DOUBLE,
            sentiment_label STRING,
            language STRING,
            region STRING,
            raw_payload STRING,
            ingestion_time TIMESTAMP NOT NULL,
            _partition_date DATE NOT NULL
        ) USING iceberg
        PARTITIONED BY (_partition_date, source)
        TBLPROPERTIES (
            'write.format.default' = 'parquet',
            'write.parquet.compression-codec' = 'snappy',
            'write.metadata.delete-after-commit.enabled' = 'true',
            'write.metadata.previous-versions-max' = '10'
        )
        """
        self.spark.sql(create_sql)
        logger.info("Created bronze.news table")

    def write_articles(self, articles: List[Dict[str, Any]]):
        """
        Write news articles to Bronze layer

        Args:
            articles: List of article dicts with keys:
                - id, published_at, source, title, summary, url,
                  symbols, sentiment_score, sentiment_label, etc.
        """
        if not articles:
            logger.warning("No articles to write")
            return

        # Transform to match schema
        records = []
        ingestion_time = datetime.now()

        for article in articles:
            published_at = article.get("published_at", int(datetime.now().timestamp() * 1000))
            partition_date = datetime.fromtimestamp(published_at / 1000).date()

            record = {
                "id": article.get("id", f"{article['source']}_{published_at}_{hash(article['title'])}"),
                "event_time": published_at,
                "source": article["source"],
                "title": article["title"],
                "summary": article.get("summary", ""),
                "content": article.get("content", ""),
                "url": article["url"],
                "author": article.get("author"),
                "symbols": article.get("symbols", []),
                "tags": article.get("tags", []),
                "sentiment_score": article.get("sentiment_score"),
                "sentiment_label": article.get("sentiment_label"),
                "language": article.get("language", "en"),
                "region": article.get("region", "global"),
                "raw_payload": str(article),
                "ingestion_time": ingestion_time,
                "_partition_date": partition_date,
            }
            records.append(record)

        # Create DataFrame
        df = self.spark.createDataFrame(records, schema=self.schema)

        # Write to Iceberg (append mode)
        df.writeTo(self.table_name).append()

        logger.info(f"Wrote {len(records)} articles to bronze.news")

    def write_from_kafka(self, kafka_df):
        """
        Write news from Kafka stream to Bronze layer

        Args:
            kafka_df: Streaming DataFrame from Kafka
        """
        from pyspark.sql.functions import from_json, col, current_timestamp, to_date

        # Parse JSON from Kafka
        parsed_df = kafka_df.select(
            from_json(col("value").cast("string"), self.schema).alias("data")
        ).select("data.*")

        # Add metadata
        enriched_df = parsed_df \
            .withColumn("ingestion_time", current_timestamp()) \
            .withColumn("_partition_date", to_date(col("event_time") / 1000))

        # Write stream
        query = enriched_df.writeStream \
            .format("iceberg") \
            .outputMode("append") \
            .option("checkpointLocation", "/tmp/checkpoint/bronze_news") \
            .toTable(self.table_name)

        return query
