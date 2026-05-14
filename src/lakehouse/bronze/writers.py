"""
Bronze Layer - Raw Data Ingestion
Stores raw data from all sources without transformation
"""
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import StreamTableEnvironment, EnvironmentSettings
from pyflink.table.expressions import col
import os


class BronzeTickerWriter:
    """Write raw ticker data to Bronze layer (Iceberg)"""

    def __init__(self, table_env: StreamTableEnvironment):
        self.table_env = table_env
        self.catalog_name = "iceberg_catalog"
        self.database_name = "bronze"
        self.table_name = "ticker"

    def create_table(self):
        """Create Bronze ticker table if not exists"""
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.catalog_name}.{self.database_name}.{self.table_name} (
            event_time BIGINT,
            symbol STRING,
            exchange STRING,
            price DOUBLE,
            volume DOUBLE,
            quote_volume DOUBLE,
            change_24h DOUBLE,
            high_24h DOUBLE,
            low_24h DOUBLE,
            raw_payload STRING,
            ingestion_time TIMESTAMP(3),
            source_system STRING,
            _partition_date DATE
        ) PARTITIONED BY (_partition_date, exchange)
        WITH (
            'write.format.default' = 'parquet',
            'write.parquet.compression-codec' = 'snappy'
        )
        """
        self.table_env.execute_sql(create_table_sql)

    def write(self, source_table: str):
        """Write from Kafka source to Bronze table"""
        insert_sql = f"""
        INSERT INTO {self.catalog_name}.{self.database_name}.{self.table_name}
        SELECT
            event_time,
            symbol,
            exchange,
            price,
            volume,
            quote_volume,
            change_24h,
            high_24h,
            low_24h,
            CAST(ROW(event_time, symbol, exchange, price, volume) AS STRING) as raw_payload,
            CURRENT_TIMESTAMP as ingestion_time,
            'flink_streaming' as source_system,
            CAST(TO_DATE(FROM_UNIXTIME(event_time / 1000)) AS DATE) as _partition_date
        FROM {source_table}
        """
        return self.table_env.execute_sql(insert_sql)


class BronzeKlineWriter:
    """Write raw kline data to Bronze layer (Iceberg)"""

    def __init__(self, table_env: StreamTableEnvironment):
        self.table_env = table_env
        self.catalog_name = "iceberg_catalog"
        self.database_name = "bronze"
        self.table_name = "kline"

    def create_table(self):
        """Create Bronze kline table if not exists"""
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.catalog_name}.{self.database_name}.{self.table_name} (
            event_time BIGINT,
            symbol STRING,
            exchange STRING,
            `interval` STRING,
            open_price DOUBLE,
            high_price DOUBLE,
            low_price DOUBLE,
            close_price DOUBLE,
            volume DOUBLE,
            quote_volume DOUBLE,
            trade_count BIGINT,
            is_closed BOOLEAN,
            raw_payload STRING,
            ingestion_time TIMESTAMP(3),
            source_system STRING,
            _partition_date DATE
        ) PARTITIONED BY (_partition_date, exchange, `interval`)
        WITH (
            'write.format.default' = 'parquet',
            'write.parquet.compression-codec' = 'snappy'
        )
        """
        self.table_env.execute_sql(create_table_sql)

    def write(self, source_table: str):
        """Write from Kafka source to Bronze table"""
        insert_sql = f"""
        INSERT INTO {self.catalog_name}.{self.database_name}.{self.table_name}
        SELECT
            event_time,
            symbol,
            exchange,
            `interval`,
            open_price,
            high_price,
            low_price,
            close_price,
            volume,
            quote_volume,
            trade_count,
            is_closed,
            CAST(ROW(event_time, symbol, exchange, open_price, close_price) AS STRING) as raw_payload,
            CURRENT_TIMESTAMP as ingestion_time,
            'flink_streaming' as source_system,
            CAST(TO_DATE(FROM_UNIXTIME(event_time / 1000)) AS DATE) as _partition_date
        FROM {source_table}
        """
        return self.table_env.execute_sql(insert_sql)


class BronzeNewsWriter:
    """Write raw news data to Bronze layer (Iceberg)"""

    def __init__(self, table_env: StreamTableEnvironment):
        self.table_env = table_env
        self.catalog_name = "iceberg_catalog"
        self.database_name = "bronze"
        self.table_name = "news"

    def create_table(self):
        """Create Bronze news table if not exists"""
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.catalog_name}.{self.database_name}.{self.table_name} (
            event_time BIGINT,
            source STRING,
            title STRING,
            content STRING,
            url STRING,
            author STRING,
            symbols ARRAY<STRING>,
            sentiment_score DOUBLE,
            raw_payload STRING,
            ingestion_time TIMESTAMP(3),
            source_system STRING,
            _partition_date DATE
        ) PARTITIONED BY (_partition_date, source)
        WITH (
            'write.format.default' = 'parquet',
            'write.parquet.compression-codec' = 'snappy'
        )
        """
        self.table_env.execute_sql(create_table_sql)

    def write(self, source_table: str):
        """Write from Kafka source to Bronze table"""
        insert_sql = f"""
        INSERT INTO {self.catalog_name}.{self.database_name}.{self.table_name}
        SELECT
            event_time,
            source,
            title,
            content,
            url,
            author,
            symbols,
            sentiment_score,
            CAST(ROW(event_time, source, title, sentiment_score) AS STRING) as raw_payload,
            CURRENT_TIMESTAMP as ingestion_time,
            'dagster_batch' as source_system,
            CAST(TO_DATE(FROM_UNIXTIME(event_time / 1000)) AS DATE) as _partition_date
        FROM {source_table}
        """
        return self.table_env.execute_sql(insert_sql)
