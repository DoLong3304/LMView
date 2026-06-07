"""
Gold Layer Aggregation via Trino HTTP API.
More stable than Spark batch for current local runtime.
"""
from __future__ import annotations

import json
import logging
import time
import urllib.request

TRINO_URL = "http://trino:8080/v1/statement"
HEADERS = {
    "X-Trino-User": "gold-aggregator",
    "X-Trino-Catalog": "iceberg",
    "X-Trino-Schema": "crypto_lakehouse",
}

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def run_query(sql: str):
    req = urllib.request.Request(TRINO_URL, data=sql.encode("utf-8"), headers=HEADERS)
    with urllib.request.urlopen(req) as resp:
        payload = json.load(resp)
    next_uri = payload.get("nextUri")
    while next_uri:
        with urllib.request.urlopen(next_uri) as resp:
            payload = json.load(resp)
        if payload.get("error"):
            raise RuntimeError(payload["error"])
        next_uri = payload.get("nextUri")
        time.sleep(0.05)
    if payload.get("error"):
        raise RuntimeError(payload["error"])
    return payload.get("data", [])


def ensure_tables():
    statements = [
        """
        CREATE TABLE IF NOT EXISTS gold_movers_ranking (
            symbol VARCHAR,
            exchange VARCHAR,
            price DOUBLE,
            change_24h DOUBLE,
            volume_24h DOUBLE,
            rank_gainers INTEGER,
            rank_losers INTEGER,
            computed_at TIMESTAMP(6) WITH TIME ZONE,
            _partition_date DATE
        ) WITH (format='PARQUET', partitioning=ARRAY['_partition_date'])
        """,
        """
        CREATE TABLE IF NOT EXISTS gold_market_dominance (
            symbol VARCHAR,
            exchange VARCHAR,
            volume_24h DOUBLE,
            volume_pct DOUBLE,
            computed_at TIMESTAMP(6) WITH TIME ZONE,
            active_symbols INTEGER,
            total_volume_24h DOUBLE,
            btc_dominance_pct DOUBLE,
            eth_dominance_pct DOUBLE,
            _partition_date DATE
        ) WITH (format='PARQUET', partitioning=ARRAY['_partition_date'])
        """,
        """
        CREATE TABLE IF NOT EXISTS gold_volatility_ranking (
            symbol VARCHAR,
            exchange VARCHAR,
            price_range_pct DOUBLE,
            atr_estimate DOUBLE,
            rank INTEGER,
            computed_at TIMESTAMP(6) WITH TIME ZONE,
            _partition_date DATE
        ) WITH (format='PARQUET', partitioning=ARRAY['_partition_date'])
        """,
        """
        CREATE TABLE IF NOT EXISTS gold_momentum_indicators (
            symbol VARCHAR,
            exchange VARCHAR,
            rsi_signal VARCHAR,
            trend_direction VARCHAR,
            macd_signal VARCHAR,
            score DOUBLE,
            computed_at TIMESTAMP(6) WITH TIME ZONE,
            _partition_date DATE
        ) WITH (format='PARQUET', partitioning=ARRAY['_partition_date'])
        """,
        """
        CREATE TABLE IF NOT EXISTS gold_sector_performance (
            sector VARCHAR,
            avg_change_pct DOUBLE,
            total_volume DOUBLE,
            symbol_count INTEGER,
            computed_at TIMESTAMP(6) WITH TIME ZONE,
            _partition_date DATE
        ) WITH (format='PARQUET', partitioning=ARRAY['_partition_date'])
        """,
        """
        CREATE TABLE IF NOT EXISTS gold_news_sentiment_daily (
            date TIMESTAMP(6) WITH TIME ZONE,
            symbol VARCHAR,
            avg_sentiment DOUBLE,
            article_count BIGINT,
            bullish_count BIGINT,
            bearish_count BIGINT,
            _partition_date DATE
        ) WITH (format='PARQUET', partitioning=ARRAY['_partition_date'])
        """,
    ]
    for sql in statements:
        run_query(sql)


def clear_today():
    for table in [
        "gold_movers_ranking",
        "gold_market_dominance",
        "gold_volatility_ranking",
        "gold_momentum_indicators",
        "gold_sector_performance",
    ]:
        run_query(f"DELETE FROM {table} WHERE _partition_date = CURRENT_DATE")


def populate_movers():
    run_query(
        """
        INSERT INTO gold_movers_ranking
        WITH latest AS (
            SELECT * FROM (
                SELECT event_time, symbol, exchange, close AS price, h24_open, h24_volume,
                       row_number() OVER (PARTITION BY symbol, exchange ORDER BY event_time DESC) rn
                FROM coin_ticker
                WHERE h24_open IS NOT NULL AND h24_open > 0
            ) t WHERE rn = 1
        ), enriched AS (
            SELECT symbol, exchange, price,
                   ((price - h24_open) / h24_open) * 100 AS change_24h,
                   h24_volume AS volume_24h
            FROM latest
        ), gainers AS (
            SELECT symbol, exchange, price, change_24h, volume_24h,
                   row_number() OVER (ORDER BY change_24h DESC) AS rank_gainers,
                   CAST(NULL AS INTEGER) AS rank_losers
            FROM enriched
            WHERE change_24h > 0
            ORDER BY change_24h DESC
            LIMIT 100
        ), losers AS (
            SELECT symbol, exchange, price, change_24h, volume_24h,
                   CAST(NULL AS INTEGER) AS rank_gainers,
                   row_number() OVER (ORDER BY change_24h ASC) AS rank_losers
            FROM enriched
            WHERE change_24h < 0
            ORDER BY change_24h ASC
            LIMIT 100
        )
        SELECT symbol, exchange, price, change_24h, volume_24h,
               rank_gainers, rank_losers, current_timestamp, CURRENT_DATE
        FROM gainers
        UNION ALL
        SELECT symbol, exchange, price, change_24h, volume_24h,
               rank_gainers, rank_losers, current_timestamp, CURRENT_DATE
        FROM losers
        """
    )


def populate_dominance():
    run_query(
        """
        INSERT INTO gold_market_dominance
        WITH latest AS (
            SELECT * FROM (
                SELECT symbol, exchange, h24_volume,
                       row_number() OVER (PARTITION BY symbol, exchange ORDER BY event_time DESC) rn
                FROM coin_ticker
            ) t WHERE rn = 1
        ), totals AS (
            SELECT SUM(h24_volume) AS total_volume_24h,
                   COUNT(*) AS active_symbols,
                   SUM(CASE WHEN symbol = 'BTCUSDT' THEN h24_volume ELSE 0 END) AS btc_volume,
                   SUM(CASE WHEN symbol = 'ETHUSDT' THEN h24_volume ELSE 0 END) AS eth_volume
            FROM latest
        )
        SELECT l.symbol, l.exchange, l.h24_volume,
               (l.h24_volume / NULLIF(t.total_volume_24h, 0)) * 100 AS volume_pct,
               current_timestamp,
               CAST(t.active_symbols AS INTEGER),
               t.total_volume_24h,
               (t.btc_volume / NULLIF(t.total_volume_24h, 0)) * 100 AS btc_dominance_pct,
               (t.eth_volume / NULLIF(t.total_volume_24h, 0)) * 100 AS eth_dominance_pct,
               CURRENT_DATE
        FROM latest l CROSS JOIN totals t
        """
    )


def populate_volatility():
    run_query(
        """
        INSERT INTO gold_volatility_ranking
        WITH recent AS (
            SELECT * FROM (
                SELECT symbol, exchange, high, low, close,
                       row_number() OVER (PARTITION BY symbol, exchange ORDER BY kline_start DESC) rn
                FROM coin_klines
                WHERE is_closed = true
            ) t WHERE rn <= 60
        ), stats AS (
            SELECT symbol, exchange,
                   ((max(high) - min(low)) / NULLIF(avg(close), 0)) * 100 AS price_range_pct
            FROM recent
            GROUP BY 1,2
        )
        SELECT symbol, exchange, price_range_pct,
               price_range_pct / 100.0 AS atr_estimate,
               row_number() OVER (ORDER BY price_range_pct DESC) AS rank,
               current_timestamp,
               CURRENT_DATE
        FROM stats
        ORDER BY price_range_pct DESC
        LIMIT 200
        """
    )


def populate_momentum():
    run_query(
        """
        INSERT INTO gold_momentum_indicators
        WITH recent AS (
            SELECT * FROM (
                SELECT symbol, exchange, close,
                       avg(close) OVER (
                           PARTITION BY symbol, exchange
                           ORDER BY kline_start
                           ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                       ) AS sma20,
                       row_number() OVER (PARTITION BY symbol, exchange ORDER BY kline_start DESC) rn
                FROM coin_klines
                WHERE is_closed = true
            ) t WHERE rn = 1
        )
        SELECT symbol, exchange,
               'neutral' AS rsi_signal,
               CASE WHEN close > sma20 THEN 'up' WHEN close < sma20 THEN 'down' ELSE 'sideways' END AS trend_direction,
               'none' AS macd_signal,
               CASE WHEN close > sma20 THEN 0.25 WHEN close < sma20 THEN -0.25 ELSE 0.0 END AS score,
               current_timestamp,
               CURRENT_DATE
        FROM recent
        """
    )


def populate_sector():
    run_query(
        """
        INSERT INTO gold_sector_performance
        WITH latest AS (
            SELECT * FROM (
                SELECT symbol, exchange, close AS price, h24_open, h24_volume,
                       row_number() OVER (PARTITION BY symbol, exchange ORDER BY event_time DESC) rn
                FROM coin_ticker
                WHERE h24_open IS NOT NULL AND h24_open > 0
            ) t WHERE rn = 1
        ), tagged AS (
            SELECT CASE
                    WHEN h24_volume > 1000000 THEN 'Large Cap'
                    WHEN h24_volume > 100000 THEN 'Mid Cap'
                    ELSE 'Small Cap'
                   END AS sector,
                   ((price - h24_open) / h24_open) * 100 AS change_24h,
                   h24_volume
            FROM latest
        )
        SELECT sector,
               avg(change_24h),
               sum(h24_volume),
               CAST(count(*) AS INTEGER),
               current_timestamp,
               CURRENT_DATE
        FROM tagged
        GROUP BY sector
        """
    )


def main():
    logger.info("Ensuring gold tables")
    ensure_tables()
    logger.info("Clearing today partitions")
    clear_today()
    logger.info("Populating movers")
    populate_movers()
    logger.info("Populating dominance")
    populate_dominance()
    logger.info("Populating volatility")
    populate_volatility()
    logger.info("Populating momentum")
    populate_momentum()
    logger.info("Populating sector")
    populate_sector()
    logger.info("Gold aggregation via Trino complete")


if __name__ == "__main__":
    main()
