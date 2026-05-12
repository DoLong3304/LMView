#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from dagster import (
    AssetExecutionContext,
    Definitions,
    ScheduleDefinition,
    asset,
    get_dagster_logger,
)

PROJECT_DIR = Path(os.environ.get("CRYPTO_PROJECT_DIR", "/app"))

SPARK_HOME = Path(os.environ.get("SPARK_HOME", "/opt/spark"))

SPARK_EVENTS_DIR = Path(os.environ.get("SPARK_EVENTS_DIR", "/opt/spark-events"))

SPARK_MASTER = os.environ.get("SPARK_MASTER", "spark://spark-master:7077")

SPARK_PACKAGES = ",".join([
    "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.2",
    "org.apache.iceberg:iceberg-aws-bundle:1.5.2",
    "org.apache.hadoop:hadoop-aws:3.3.4",
    "org.postgresql:postgresql:42.7.2",
])

# Add project src to Python path for news modules
sys.path.insert(0, str(PROJECT_DIR / "src"))

def _run_spark_job(context: AssetExecutionContext, script_name: str, extra_args: Optional[List[str]] = None) -> None:
    logger = get_dagster_logger()
    script_path = PROJECT_DIR / "src" / script_name

    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")

    SPARK_EVENTS_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(SPARK_HOME / "bin" / "spark-submit"),
        "--master", SPARK_MASTER,
        "--packages", SPARK_PACKAGES,
        "--conf", "spark.eventLog.enabled=true",
        "--conf", f"spark.eventLog.dir=file://{SPARK_EVENTS_DIR}",
        str(script_path),
    ]

    if extra_args:
        cmd.extend(extra_args)

    logger.info("Running command: %s", " ".join(cmd))

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,    # merge stderr into stdout for a single stream
        text=True,
        bufsize=1,                   # line-buffered
        cwd=str(PROJECT_DIR),
    )

    for line in process.stdout:
        line = line.rstrip()
        if line:
            logger.info(line)

    process.wait()

    if process.returncode != 0:
        raise Exception(
            f"Spark job '{script_name}' failed with exit code {process.returncode}. "
            f"Check logs in Dagster UI or Spark History Server (http://localhost:18080)."
        )

    logger.info("Spark job '%s' completed successfully.", script_name)


@asset(
    description=(
        "Pulls 1h OHLCV klines from Binance API for all USDT pairs, "
        "fetches only rows newer than the last run, then writes to Iceberg "
        "table. Also detects & fills InfluxDB gaps from machine downtime."
    ),
    group_name="ingestion",
)
def backfill_historical(context: AssetExecutionContext) -> None:
    _run_spark_job(
        context,
        script_name="batch/backfill.py",
        extra_args=["--mode", "all", "--iceberg-mode", "incremental"],
    )


@asset(
    description=(
        "Aggregates 1-minute candles into hourly candles to reduce data bloat. "
        "Runs on both InfluxDB (candles measurement) and Iceberg (coin_klines table). "
        "Deletes 1m data older than RETENTION_1M_DAYS (default: 90 days)."
    ),
    group_name="maintenance",
)
def aggregate_candles(context: AssetExecutionContext) -> None:
    _run_spark_job(
        context,
        script_name="batch/aggregate.py",
        extra_args=["--mode", "all"],
    )


@asset(
    description=(
        "Runs 4 maintenance tasks on Iceberg tables: "
        "(1) Compact small files into ~128 MB files, "
        "(2) Rewrite manifests to reduce metadata overhead, "
        "(3) Expire snapshots older than 48 hours, "
        "(4) Remove orphan files no longer referenced."
    ),
    group_name="maintenance",
)
def iceberg_table_maintenance(context: AssetExecutionContext) -> None:
    _run_spark_job(
        context,
        script_name="batch/maintenance.py",
    )


schedule_weekly_maintenance = ScheduleDefinition(
    name="weekly_iceberg_maintenance",
    target=iceberg_table_maintenance,
    cron_schedule="0 3 * * 0",
    description="Runs every Sunday at 03:00 AM to compact and clean up Iceberg tables.",
)

schedule_daily_aggregate = ScheduleDefinition(
    name="daily_candle_aggregation",
    target=aggregate_candles,
    cron_schedule="0 4 * * *",
    description="Runs daily at 04:00 AM to aggregate 1m candles into 1h and clean up old 1m data.",
)

@asset(
    description="Scrapes crypto news from CryptoPanic and publishes sentiment analysis to Kafka"
)
def news_sentiment_pipeline(context: AssetExecutionContext) -> None:
    """Fetch news, analyze sentiment, and publish to Kafka.

    Runs every 5 minutes via schedule_news_sentiment.
    """
    logger = get_dagster_logger()

    try:
        from news.scraper import NewsScraper
        from news.sentiment_analyzer import SentimentAnalyzer
        from common.kafka_client import init_producer, send_to_kafka, flush_and_close
        from common.avro_serializer import AvroSerializer
        from common.config import SCHEMA_REGISTRY_URL
        import time

        logger.info("Starting news sentiment pipeline...")

        # Initialize components
        scraper = NewsScraper()
        analyzer = SentimentAnalyzer()

        # Initialize Kafka producer
        init_producer()
        avro_serializer = AvroSerializer(SCHEMA_REGISTRY_URL)
        schema_path = PROJECT_DIR / "schemas" / "news.avsc"
        avro_serializer.register("crypto_news_sentiment", str(schema_path))

        # Fetch latest news
        news_items = scraper.fetch_latest(
            currencies=["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "DOGE", "MATIC", "DOT", "AVAX"],
            limit=20,
            filter_type="hot"
        )

        logger.info(f"Fetched {len(news_items)} news items")

        # Process each news item
        published_count = 0
        for item in news_items:
            try:
                # Analyze sentiment
                title = item.get("title", "")
                sentiment_score = analyzer.analyze(title)

                # Format for Kafka
                record = scraper.format_for_kafka(item, sentiment_score)

                # Publish to Kafka
                send_to_kafka("crypto_news_sentiment", record, avro_serializer)
                published_count += 1

                logger.info(
                    f"Published: {title[:60]}... | sentiment={sentiment_score:.3f} | symbols={record['symbols']}"
                )

            except Exception as e:
                logger.error(f"Failed to process news item: {e}")
                continue

        # Flush Kafka producer
        flush_and_close()

        logger.info(f"News sentiment pipeline completed. Published {published_count}/{len(news_items)} items.")

    except Exception as e:
        logger.error(f"News sentiment pipeline failed: {e}")
        raise


defs = Definitions(
    assets=[
        backfill_historical,
        aggregate_candles,
        iceberg_table_maintenance,
        news_sentiment_pipeline,
    ],
    schedules=[
        schedule_weekly_maintenance,
        schedule_daily_aggregate,
        ScheduleDefinition(
            name="schedule_news_sentiment",
            target=news_sentiment_pipeline,
            cron_schedule="*/5 * * * *",  # Every 5 minutes
            execution_timezone="UTC",
        ),
    ],
)
