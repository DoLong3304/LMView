"""
Flink Streaming Job - Real-time Price Change Calculator
Calculates % price change for each symbol and updates Redis cache
Updates every second, replaces existing value (no duplication)

Architecture:
1. Read from silver.ticker_unified (streaming)
2. Calculate price_change_pct = ((current - reference) / reference) × 100
3. Write to Redis with TTL (key: price_change:{symbol})
4. Redis automatically replaces old value (no duplication)
"""
import os
import sys
from pathlib import Path

# Add project to path
PROJECT_DIR = Path("/app")
sys.path.insert(0, str(PROJECT_DIR / "src"))

from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import StreamTableEnvironment, EnvironmentSettings
from pyflink.table.expressions import col, lit
from pyflink.table.window import Tumble
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def create_table_env():
    """Create Flink Table Environment with Iceberg + Redis connectors"""
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(4)

    settings = EnvironmentSettings.new_instance() \
        .in_streaming_mode() \
        .build()

    table_env = StreamTableEnvironment.create(env, settings)

    # Add Iceberg catalog
    table_env.execute_sql(f"""
        CREATE CATALOG iceberg_catalog WITH (
            'type' = 'iceberg',
            'catalog-type' = 'hadoop',
            'warehouse' = 's3a://cryptoprice/warehouse',
            'property-version' = '1'
        )
    """)

    table_env.use_catalog("iceberg_catalog")

    return table_env


def create_redis_sink(table_env: StreamTableEnvironment):
    """Create Redis sink table for price change data"""

    # Redis Sentinel configuration
    redis_sentinels = os.getenv("REDIS_SENTINELS", "redis-sentinel-1:26379,redis-sentinel-2:26379,redis-sentinel-3:26379")
    redis_master = os.getenv("REDIS_MASTER_NAME", "mymaster")

    table_env.execute_sql(f"""
        CREATE TABLE redis_price_change (
            symbol STRING,
            current_price DOUBLE,
            reference_price DOUBLE,
            change_pct DOUBLE,
            change_abs DOUBLE,
            snapshot_time BIGINT,
            PRIMARY KEY (symbol) NOT ENFORCED
        ) WITH (
            'connector' = 'redis',
            'mode' = 'sentinel',
            'sentinels' = '{redis_sentinels}',
            'master-name' = '{redis_master}',
            'key-pattern' = 'price_change:${{symbol}}',
            'value-format' = 'json',
            'ttl' = '60'
        )
    """)

    logger.info("Created Redis sink table")


def create_reference_price_table(table_env: StreamTableEnvironment):
    """
    Create table to store reference prices (opening price of the day)
    Uses Flink state to maintain reference price per symbol
    """

    table_env.execute_sql("""
        CREATE TABLE reference_prices (
            symbol STRING,
            reference_price DOUBLE,
            reference_time BIGINT,
            PRIMARY KEY (symbol) NOT ENFORCED
        ) WITH (
            'connector' = 'upsert-kafka',
            'topic' = 'reference_prices',
            'properties.bootstrap.servers' = 'kafka-1:9092,kafka-2:9092,kafka-3:9092',
            'key.format' = 'raw',
            'value.format' = 'json'
        )
    """)

    logger.info("Created reference_prices table")


def calculate_price_change(table_env: StreamTableEnvironment):
    """
    Main calculation logic:
    1. Read ticker_unified stream
    2. Get reference price (opening price at 00:00 UTC)
    3. Calculate % change
    4. Write to Redis (replaces old value automatically)
    """

    logger.info("Starting price change calculation...")

    # Read from Silver ticker_unified (streaming)
    table_env.execute_sql("""
        CREATE TABLE IF NOT EXISTS silver_ticker_stream (
            event_time BIGINT,
            symbol STRING,
            price_mid DOUBLE,
            volume_total DOUBLE,
            event_timestamp AS TO_TIMESTAMP(FROM_UNIXTIME(event_time / 1000)),
            WATERMARK FOR event_timestamp AS event_timestamp - INTERVAL '10' SECOND
        ) WITH (
            'connector' = 'iceberg',
            'catalog-name' = 'iceberg_catalog',
            'database-name' = 'silver',
            'table-name' = 'ticker_unified'
        )
    """)

    # Get latest price per symbol (1-second tumbling window)
    latest_prices = table_env.sql_query("""
        SELECT
            symbol,
            LAST_VALUE(price_mid) AS current_price,
            LAST_VALUE(event_time) AS snapshot_time,
            TUMBLE_END(event_timestamp, INTERVAL '1' SECOND) AS window_end
        FROM silver_ticker_stream
        GROUP BY
            symbol,
            TUMBLE(event_timestamp, INTERVAL '1' SECOND)
    """)

    table_env.create_temporary_view("latest_prices", latest_prices)

    # Get reference price (first price of the day at 00:00 UTC)
    # Use session window to track daily opening price
    reference_prices = table_env.sql_query("""
        SELECT
            symbol,
            FIRST_VALUE(price_mid) AS reference_price,
            FIRST_VALUE(event_time) AS reference_time
        FROM silver_ticker_stream
        WHERE HOUR(event_timestamp) = 0 AND MINUTE(event_timestamp) = 0
        GROUP BY symbol
    """)

    table_env.create_temporary_view("reference_prices", reference_prices)

    # Calculate price change %
    price_change = table_env.sql_query("""
        SELECT
            l.symbol,
            l.current_price,
            COALESCE(r.reference_price, l.current_price) AS reference_price,
            CASE
                WHEN COALESCE(r.reference_price, l.current_price) > 0
                THEN ((l.current_price - COALESCE(r.reference_price, l.current_price))
                      / COALESCE(r.reference_price, l.current_price)) * 100
                ELSE 0
            END AS change_pct,
            l.current_price - COALESCE(r.reference_price, l.current_price) AS change_abs,
            l.snapshot_time
        FROM latest_prices l
        LEFT JOIN reference_prices r
        ON l.symbol = r.symbol
    """)

    # Write to Redis (upsert mode - replaces old value)
    price_change.execute_insert("redis_price_change")

    logger.info("Price change calculation pipeline started")


def main():
    """Main Flink job"""
    logger.info("=" * 80)
    logger.info("Starting Flink Price Change Streaming Job")
    logger.info("=" * 80)

    try:
        # Create table environment
        table_env = create_table_env()

        # Create Redis sink
        create_redis_sink(table_env)

        # Create reference price table
        create_reference_price_table(table_env)

        # Start calculation
        calculate_price_change(table_env)

        logger.info("Flink job submitted successfully")
        logger.info("Price change % will be calculated every second and updated to Redis")
        logger.info("Redis key pattern: price_change:{symbol}")
        logger.info("TTL: 60 seconds (auto-cleanup)")

    except Exception as e:
        logger.error(f"Flink job failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
