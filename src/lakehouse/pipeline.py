#!/usr/bin/env python3
"""
Spark Structured Streaming pipeline: Kafka â†’ Iceberg tables.

Reads Avro-encoded messages from Kafka topics (ticker, trades, klines),
deserializes them, and writes to Iceberg tables partitioned by day.

Usage (Docker)::

    spark-submit /app/src/lakehouse/pipeline.py
"""

import json
import os
import sys
import time
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_timestamp

logger = logging.getLogger(__name__)
from pyspark.sql.avro.functions import from_avro

from common.config import (
    KAFKA_BOOTSTRAP,
    ICEBERG_TABLE_TICKER,
    ICEBERG_TABLE_TRADES,
    ICEBERG_TABLE_KLINES,
    MINIO_ENDPOINT,
    MINIO_ACCESS_KEY,
    MINIO_SECRET_KEY,
)

# â”€â”€ Checkpoint locations â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
CHECKPOINT_TICKER = "s3://cryptoprice/checkpoints/crypto_ticker_v1"
CHECKPOINT_TRADES = "s3://cryptoprice/checkpoints/crypto_trades_v1"
CHECKPOINT_KLINES = "s3://cryptoprice/checkpoints/crypto_klines_v1"

# â”€â”€ Load Avro schemas from canonical schema files â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "schemas")


def _load_avro_schema(filename: str) -> str:
    """Load an Avro schema from the schemas/ directory as a JSON string."""
    path = os.path.join(SCHEMA_DIR, filename)
    with open(path) as f:
        return json.dumps(json.load(f))


TICKER_AVRO_SCHEMA = _load_avro_schema("ticker.avsc")
TRADES_AVRO_SCHEMA = _load_avro_schema("trade.avsc")
KLINES_AVRO_SCHEMA = _load_avro_schema("kline.avsc")


def build_spark() -> SparkSession:
    """Build a SparkSession configured for Iceberg + MinIO."""
    return (
        SparkSession.builder.appName("BinanceDualStreamToIceberg")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.extensions",
                "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
        .config("spark.sql.catalog.iceberg_catalog",
                "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.iceberg_catalog.type",            "jdbc")
        .config("spark.sql.catalog.iceberg_catalog.uri",
                f"jdbc:postgresql://{os.environ.get('POSTGRES_HOST', 'postgres')}:5432/iceberg_catalog")
        .config("spark.sql.catalog.iceberg_catalog.jdbc.user",       os.environ.get("POSTGRES_USER", ""))
        .config("spark.sql.catalog.iceberg_catalog.jdbc.password",   os.environ.get("POSTGRES_PASSWORD", ""))
        .config("spark.sql.catalog.iceberg_catalog.warehouse",
                "s3://cryptoprice/iceberg")
        .config("spark.sql.catalog.iceberg_catalog.io-impl",
                "org.apache.iceberg.aws.s3.S3FileIO")
        .config("spark.sql.catalog.iceberg_catalog.s3.endpoint",          MINIO_ENDPOINT)
        .config("spark.sql.catalog.iceberg_catalog.s3.access-key-id",     MINIO_ACCESS_KEY)
        .config("spark.sql.catalog.iceberg_catalog.s3.secret-access-key", MINIO_SECRET_KEY)
        .config("spark.sql.catalog.iceberg_catalog.s3.path-style-access", "true")
        .config("spark.sql.catalog.iceberg_catalog.client.region",        "us-east-1")
        .config("spark.hadoop.fs.s3a.endpoint",         MINIO_ENDPOINT)
        .config("spark.hadoop.fs.s3a.access.key",       MINIO_ACCESS_KEY)
        .config("spark.hadoop.fs.s3a.secret.key",       MINIO_SECRET_KEY)
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.impl",
                "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config("spark.hadoop.fs.s3.impl",
                "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
        .config("spark.hadoop.fs.s3a.aws.credentials.provider",
                "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider")
        .config("spark.sql.defaultCatalog", "iceberg_catalog")
        .config("spark.streaming.stopGracefullyOnShutdown", "true")
        .config("spark.streaming.backpressure.enabled", "true")
        .config("spark.task.maxFailures", "4")
        .config("spark.cores.max", "2")
        .getOrCreate()
    )


def read_kafka(spark: SparkSession, topic: str, avro_schema: str):
    """Read from Kafka and deserialize Confluent Avro format.

    Confluent wire format: [magic_byte:1][schema_id:4][avro_binary:N]
    We strip the first 5 bytes before passing to from_avro().
    """
    return (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP)
        .option("subscribe", topic)
        .option("startingOffsets", "latest")
        .option("failOnDataLoss", "false")
        .option("maxOffsetsPerTrigger", 500_000)
        .load()
        .selectExpr("substring(value, 6, length(value)-5) as avro_value")
        .select(from_avro(col("avro_value"), avro_schema).alias("data"))
        .select("data.*")
    )


def _ensure_column(spark: SparkSession, table_name: str, column_name: str, column_type: str) -> None:
    """Best-effort schema evolution for existing Iceberg tables."""
    try:
        spark.sql(f"ALTER TABLE {table_name} ADD COLUMNS ({column_name} {column_type})")
        logger.info("Added column %s %s to %s", column_name, column_type, table_name)
    except Exception as exc:
        message = str(exc)
        if "already exists" in message or "Cannot add duplicate" in message or "Found duplicate column" in message:
            logger.info("Column %s already exists on %s", column_name, table_name)
        else:
            logger.warning("Could not add column %s to %s: %s", column_name, table_name, exc)

def _start_query_with_retry(start_query_fn, query_name: str, max_retries: int = 5, backoff_sec: int = 15):
    """Start streaming query with bounded retries.

    Retries cover startup-time failures only. Once all queries are started,
    Spark owns runtime supervision until `awaitAnyTermination()` returns.
    """
    attempt = 0
    while True:
        try:
            query = start_query_fn()
            logger.info("Started streaming query %s", query_name)
            return query
        except Exception as exc:
            attempt += 1
            logger.exception("Failed starting query %s (attempt %d/%d): %s", query_name, attempt, max_retries, exc)
            if attempt >= max_retries:
                raise
            time.sleep(backoff_sec * attempt)


def run():
    spark = build_spark()
    spark.sparkContext.setLogLevel("WARN")

    # â”€â”€ Ensure Iceberg database + tables exist â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    spark.sql("CREATE DATABASE IF NOT EXISTS iceberg_catalog.crypto_lakehouse")

    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {ICEBERG_TABLE_TICKER} (
            event_time          BIGINT,
            symbol              STRING,
            exchange            STRING,
            close               DOUBLE,
            bid                 DOUBLE,
            ask                 DOUBLE,
            h24_open            DOUBLE,
            h24_high            DOUBLE,
            h24_low             DOUBLE,
            h24_volume          DOUBLE,
            h24_quote_volume    DOUBLE,
            h24_price_change    DOUBLE,
            h24_price_change_pct DOUBLE,
            h24_trade_count     BIGINT,
            event_timestamp     TIMESTAMP,
            ingested_at         TIMESTAMP
        )
        USING iceberg
        PARTITIONED BY (days(event_timestamp))
    """)
    _ensure_column(spark, ICEBERG_TABLE_TICKER, "exchange", "STRING")

    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {ICEBERG_TABLE_TRADES} (
            event_time      BIGINT,
            symbol          STRING,
            exchange        STRING,
            agg_trade_id    BIGINT,
            price           DOUBLE,
            quantity        DOUBLE,
            trade_time      BIGINT,
            is_buyer_maker  BOOLEAN,
            event_timestamp TIMESTAMP,
            trade_timestamp TIMESTAMP,
            ingested_at     TIMESTAMP
        )
        USING iceberg
        PARTITIONED BY (days(trade_timestamp))
    """)
    _ensure_column(spark, ICEBERG_TABLE_TRADES, "exchange", "STRING")

    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {ICEBERG_TABLE_KLINES} (
            event_time      BIGINT,
            symbol          STRING,
            exchange        STRING,
            kline_start     BIGINT,
            kline_close     BIGINT,
            interval        STRING,
            open            DOUBLE,
            high            DOUBLE,
            low             DOUBLE,
            close           DOUBLE,
            volume          DOUBLE,
            quote_volume    DOUBLE,
            trade_count     BIGINT,
            is_closed       BOOLEAN,
            kline_timestamp TIMESTAMP,
            ingested_at     TIMESTAMP
        )
        USING iceberg
        PARTITIONED BY (days(kline_timestamp))
    """)
    _ensure_column(spark, ICEBERG_TABLE_KLINES, "exchange", "STRING")

    # â”€â”€ Ticker stream â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    ticker_df = (
        read_kafka(spark, "crypto_ticker", TICKER_AVRO_SCHEMA)
        .filter(col("event_time").isNotNull())
        .withColumn("event_timestamp", (col("event_time") / 1000).cast("timestamp"))
        .withColumn("ingested_at", current_timestamp())
        .select(
            "event_time",
            "symbol",
            "close",
            "bid",
            "ask",
            "h24_open",
            "h24_high",
            "h24_low",
            "h24_volume",
            "h24_quote_volume",
            "h24_price_change",
            "h24_price_change_pct",
            "h24_trade_count",
            "event_timestamp",
            "ingested_at",
            "exchange",
        )
        .withWatermark("event_timestamp", "1 minute")
        .dropDuplicates(["symbol", "event_timestamp"])
    )

    ticker_query = _start_query_with_retry(
        lambda: ticker_df.writeStream
        .format("iceberg")
        .outputMode("append")
        .trigger(processingTime="1 minute")
        .option("checkpointLocation", CHECKPOINT_TICKER)
        .toTable(ICEBERG_TABLE_TICKER),
        "ticker",
    )

    # â”€â”€ Trades stream â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    trades_df = (
        read_kafka(spark, "crypto_trades", TRADES_AVRO_SCHEMA)
        .filter(col("event_time").isNotNull())
        .withColumn("event_timestamp", (col("event_time") / 1000).cast("timestamp"))
        .withColumn("trade_timestamp",  (col("trade_time") / 1000).cast("timestamp"))
        .withColumn("ingested_at", current_timestamp())
        .select(
            "event_time",
            "symbol",
            "agg_trade_id",
            "price",
            "quantity",
            "trade_time",
            "is_buyer_maker",
            "event_timestamp",
            "trade_timestamp",
            "ingested_at",
            "exchange",
        )
    )

    trades_query = _start_query_with_retry(
        lambda: trades_df.writeStream
        .format("iceberg")
        .outputMode("append")
        .trigger(processingTime="1 minute")
        .option("checkpointLocation", CHECKPOINT_TRADES)
        .toTable(ICEBERG_TABLE_TRADES),
        "trades",
    )

    # â”€â”€ Klines stream â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    klines_df = (
        read_kafka(spark, "crypto_klines", KLINES_AVRO_SCHEMA)
        .filter(col("kline_start").isNotNull())
        .filter(col("is_closed") == True)
        .withColumn("kline_timestamp", (col("kline_start") / 1000).cast("timestamp"))
        .withColumn("ingested_at", current_timestamp())
        .select(
            "event_time",
            "symbol",
            "kline_start",
            "kline_close",
            "interval",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "quote_volume",
            "trade_count",
            "is_closed",
            "kline_timestamp",
            "ingested_at",
            "exchange",
        )
        .withWatermark("kline_timestamp", "2 minutes")
        .dropDuplicates(["exchange", "symbol", "kline_start"])
    )

    klines_query = _start_query_with_retry(
        lambda: klines_df.writeStream
        .format("iceberg")
        .outputMode("append")
        .trigger(processingTime="1 minute")
        .option("checkpointLocation", CHECKPOINT_KLINES)
        .toTable(ICEBERG_TABLE_KLINES),
        "klines",
    )

    logger.info("All streaming queries started: %s", [q.name for q in spark.streams.active])

    # Block indefinitely so the JVM stays alive and processes records
    spark.streams.awaitAnyTermination()

if __name__ == "__main__":
    run()
