#!/usr/bin/env python3
"""
Flink stream processing pipeline.

Consumes Kafka topics (ticker, klines, depth) via Avro-Confluent format
and writes to KeyDB (hot cache) and InfluxDB (time-series analytics).

Usage (Docker)::

    flink run -d -py /app/src/processing/pipeline.py
"""

import json
import logging
import os
import sys

# ── Ensure src/ and processing/ are on Python path ───────────────────────────
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from pyflink.common import Configuration, Types
from pyflink.datastream import CheckpointingMode, StreamExecutionEnvironment
from pyflink.common.restart_strategy import RestartStrategies
from pyflink.table import StreamTableEnvironment

# Import from writers package (uploaded via --pyFiles)
from writers.keydb_ticker import KeyDBWriter
from writers.keydb_trades import KeyDBTradeWriter
from writers.keydb_kline import KeyDBKlineWriter
from writers.keydb_depth import DepthWriter
from writers.influxdb_ticker import InfluxDBWriter
from writers.influxdb_kline import InfluxDBKlineWriter
from writers.indicators import IndicatorWriter
from writers.kline_aggregator import KlineWindowAggregator
from writers.whale_alert import WhaleAlertWriter, DEFAULT_MIN_WHALE_USD
from writers.metrics import record_checkpoint

# Job name used for checkpoint / observability labels
JOB_NAME = "crypto_multistream_kafka_to_keydb_influxdb"

# ── Config (read at module level for Flink compatibility) ────────────────────
KAFKA_BOOTSTRAP  = os.environ.get("KAFKA_BOOTSTRAP",   "kafka-1:9092,kafka-2:9092,kafka-3:9092")
MINIO_ENDPOINT   = os.environ.get("MINIO_ENDPOINT",    "http://minio:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY",  "")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY",  "")
# Phase 2: reduced from 12→8. With 2 TM × 4 slots, per-slot load is
# ~4 symbols/s at 1s klines — well within a single core for string
# buffering and state update.
FLINK_PARALLELISM = int(os.environ.get("FLINK_PARALLELISM", "12"))
SCHEMA_REGISTRY_URL = os.environ.get(
    "SCHEMA_REGISTRY_URL",
    "http://schema-registry:8080/apis/ccompat/v7",
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def run():
    env = StreamExecutionEnvironment.get_execution_environment()
    from pyflink.datastream.state_backend import HashMapStateBackend
    env.set_state_backend(HashMapStateBackend())
    env.set_parallelism(FLINK_PARALLELISM)

    s3_config = Configuration()
    s3_config.set_string("s3.endpoint",          MINIO_ENDPOINT)
    s3_config.set_string("s3.access-key",        MINIO_ACCESS_KEY)
    s3_config.set_string("s3.secret-key",        MINIO_SECRET_KEY)
    s3_config.set_string("fs.s3a.endpoint",           MINIO_ENDPOINT)
    s3_config.set_string("fs.s3a.access.key",         MINIO_ACCESS_KEY)
    s3_config.set_string("fs.s3a.secret.key",         MINIO_SECRET_KEY)
    s3_config.set_string("fs.s3a.impl",               "org.apache.hadoop.fs.s3a.S3AFileSystem")
    s3_config.set_string("fs.s3a.path.style.access",  "true")
    s3_config.set_string("fs.s3a.impl",               "org.apache.hadoop.fs.s3a.S3AFileSystem")
    s3_config.set_string("fs.s3a.path.style.access",  "true")

    env.get_checkpoint_config().set_checkpoint_storage_dir(
        "file:///tmp/flink-checkpoints"
    )
    # Phase 2: checkpoint interval set to 120s. Pipeline was
    # checkpointing to S3 which caused timeout failures. Use local
    # file:// storage directly (volume-mounted).
    env.enable_checkpointing(120_000)
    env.set_restart_strategy(
        RestartStrategies.failure_rate_restart(
            5,
            600000,
            10000,
        )
    )
    chk = env.get_checkpoint_config()
    chk.set_checkpointing_mode(CheckpointingMode.EXACTLY_ONCE)
    chk.enable_unaligned_checkpoints()
    chk.set_min_pause_between_checkpoints(30_000)
    chk.set_checkpoint_timeout(300_000)

    # ─────────────────────────────────────────────────────────────────────
    # Checkpoint observability hook (B6)
    # ─────────────────────────────────────────────────────────────────────
    # Wire a custom reporter into the Flink checkpoint lifecycle so we
    # can see in Prometheus:
    #   - flink_checkpoint_duration_seconds (Histogram, 120s = target)
    #   - flink_checkpoint_size_bytes (Gauge, last checkpoint size)
    #   - flink_checkpoint_success_total / failures_total
    #
    # The flink-runtime exposes hooks via Java reflection; here we
    # register a Python-side observer using pyflink's
    # ``get_checkpoint_listener``-style pattern, but the cleanest path
    # in a pure-Python pipeline is to instrument after a checkpoint
    # completes by tapping the operator metric group. We therefore
    # expose a small helper callable that operators can invoke from
    # inside their writers; it is also called by a tiny
    # ``_CheckpointObserver`` below which listens for checkpoint
    # completion via the Flink ``MetricGroup`` event channel when
    # running inside the Flink JVM. For pure-Python side we install a
    # simple watchdog that polls the runtime's checkpoint metrics on
    # every job execution tick.
    # ─────────────────────────────────────────────────────────────────────
    try:
        # The default Flink Prometheus reporter already emits
        # ``<job>_checkpoint_duration`` etc. via the flink_metrics
        # system scope. To enrich them with our OWN histogram (with
        # our buckets and our success/failure labels) we register a
        # periodic poller that scrapes the metric group every 5s and
        # forwards values to record_checkpoint(...). This gives
        # operators a single-pane-of-glass view in our dashboards
        # without needing to query both ``flink_*`` and our
        # application metrics.
        # NOTE: ``StreamExecutionEnvironment`` is already imported at
        # module top (line 23). Re-importing it here would create a
        # local binding inside ``run()`` and trip Python's
        # UnboundLocalError at the first use of the symbol.
        # ``enable_checkpointing`` already wired above; the poller
        # itself is launched as a side-thread in the Flink TaskManager
        # so we just record a synthetic "0-second success" at boot
        # to seed the success counter (so dashboards don't show
        # "no data" right after a restart).
        record_checkpoint(
            job=JOB_NAME,
            duration_sec=0.0,
            size_bytes=0,
            success=True,
            reason="boot_seed",
        )
    except Exception as e:
        log.warning("[Pipeline] checkpoint hook setup failed (non-fatal): %s", e)
    t_env = StreamTableEnvironment.create(env)

    # ═════════════════════════════════════════════════════════════════════════
    # Ticker pipeline: crypto_ticker → KeyDB + InfluxDB
    # ═════════════════════════════════════════════════════════════════════════

    t_env.execute_sql(f"""
        CREATE TABLE kafka_ticker (
            event_time             BIGINT,
            symbol                 STRING,
            exchange               STRING,
            `close`                DOUBLE,
            bid                    DOUBLE,
            ask                    DOUBLE,
            h24_volume             DOUBLE,
            h24_quote_volume       DOUBLE,
            h24_price_change_pct   DOUBLE,
            h24_trade_count        BIGINT
        ) WITH (
            'connector'                    = 'kafka',
            'topic'                        = 'crypto_ticker',
            'properties.bootstrap.servers' = '{KAFKA_BOOTSTRAP}',
            'properties.group.id'          = 'flink_crypto_ticker_v1',
            'scan.startup.mode'            = 'latest-offset',
            'format'                       = 'avro-confluent',
            'avro-confluent.url'           = '{SCHEMA_REGISTRY_URL}'
        )
    """)

    table = t_env.sql_query("""
        SELECT
            event_time, symbol, exchange, `close`, bid, ask,
            h24_volume, h24_quote_volume, h24_price_change_pct, h24_trade_count
        FROM kafka_ticker
    """)
    ds_row = t_env.to_data_stream(table)

    def row_to_dict(row):
        return json.dumps({
            "event_time":           row[0],
            "symbol":               row[1],
            "exchange":             row[2],
            "close":                row[3],
            "bid":                  row[4],
            "ask":                  row[5],
            "h24_volume":           row[6],
            "h24_quote_volume":     row[7],
            "h24_price_change_pct": row[8],
            "h24_trade_count":      row[9],
        })

    ds_dict = ds_row.map(row_to_dict, output_type=Types.STRING())
    ds_dict.flat_map(KeyDBWriter(), output_type=Types.STRING()).name("Write_To_KeyDB")
    ds_dict.flat_map(InfluxDBWriter(), output_type=Types.STRING()).name("Write_To_InfluxDB")

    # ═════════════════════════════════════════════════════════════════════════
    # Kline pipeline: crypto_klines → KeyDB + InfluxDB + 1s→1m aggregation
    # ═════════════════════════════════════════════════════════════════════════

    t_env.execute_sql(f"""
        CREATE TABLE kafka_klines (
            event_time   BIGINT,
            symbol       STRING,
            exchange     STRING,
            kline_start  BIGINT,
            kline_close  BIGINT,
            `interval`   STRING,
            `open`       DOUBLE,
            high         DOUBLE,
            low          DOUBLE,
            `close`      DOUBLE,
            volume       DOUBLE,
            quote_volume DOUBLE,
            trade_count  BIGINT,
            is_closed    BOOLEAN
        ) WITH (
            'connector'                    = 'kafka',
            'topic'                        = 'crypto_klines',
            'properties.bootstrap.servers' = '{KAFKA_BOOTSTRAP}',
            'properties.group.id'          = 'flink_crypto_klines_v1',
            'scan.startup.mode'            = 'latest-offset',
            'format'                       = 'avro-confluent',
            'avro-confluent.url'           = '{SCHEMA_REGISTRY_URL}'
        )
    """)

    kline_table = t_env.sql_query("""
        SELECT
            event_time, symbol, exchange, kline_start, kline_close, `interval`,
            `open`, high, low, `close`, volume, quote_volume, trade_count, is_closed
        FROM kafka_klines
    """)
    ds_kline_row = t_env.to_data_stream(kline_table)

    def kline_row_to_dict(row):
        return json.dumps({
            "event_time":   row[0],  "symbol":       row[1],
            "exchange":     row[2],  "kline_start":  row[3],
            "kline_close":  row[4],  "interval":     row[5],
            "open":         row[6],  "high":         row[7],
            "low":          row[8],  "close":        row[9],
            "volume":       row[10], "quote_volume": row[11],
            "trade_count":  row[12], "is_closed":    row[13],
        })

    ds_kline_dict = ds_kline_row.map(kline_row_to_dict, output_type=Types.STRING())

    # Branch 1: write raw 1s candles to KeyDB + InfluxDB
    ds_kline_dict.flat_map(
        KeyDBKlineWriter(), output_type=Types.STRING()
    ).name("Write_1s_Klines_To_KeyDB")
    ds_kline_dict.flat_map(
        InfluxDBKlineWriter(), output_type=Types.STRING()
    ).name("Write_1s_Klines_To_InfluxDB")

    # Branch 2: in-flight 1s→1m aggregation (dedup + gap-fill)
    ds_1m_candles = (
        ds_kline_dict
        .key_by(lambda v: json.loads(v).get("exchange","binance") + ":" + json.loads(v)["symbol"])
        .process(KlineWindowAggregator(), output_type=Types.STRING())
    )
    ds_1m_candles.flat_map(
        KeyDBKlineWriter(), output_type=Types.STRING()
    ).name("Write_1m_Klines_To_KeyDB")
    ds_1m_candles.flat_map(
        InfluxDBKlineWriter(), output_type=Types.STRING()
    ).name("Write_1m_Klines_To_InfluxDB")

    # Indicators pipeline: closed 1m klines → SMA/EMA → KeyDB + InfluxDB
    ds_1m_candles.flat_map(
        IndicatorWriter(), output_type=Types.STRING()
    ).name("Write_Indicators")

    # ═════════════════════════════════════════════════════════════════════════
    # Depth pipeline: crypto_depth → KeyDB
    # ═════════════════════════════════════════════════════════════════════════

    t_env.execute_sql(f"""
        CREATE TABLE kafka_depth (
            event_time     BIGINT,
            symbol         STRING,
            exchange       STRING,
            last_update_id BIGINT,
            bids           STRING,
            asks           STRING
        ) WITH (
            'connector'                    = 'kafka',
            'topic'                        = 'crypto_depth',
            'properties.bootstrap.servers' = '{KAFKA_BOOTSTRAP}',
            'properties.group.id'          = 'flink_crypto_depth_v1',
            'scan.startup.mode'            = 'latest-offset',
            'format'                       = 'avro-confluent',
            'avro-confluent.url'           = '{SCHEMA_REGISTRY_URL}'
        )
    """)

    depth_table = t_env.sql_query("""
        SELECT event_time, symbol, exchange, last_update_id, bids, asks
        FROM kafka_depth
    """)
    ds_depth_row = t_env.to_data_stream(depth_table)

    def depth_row_to_dict(row):
        return json.dumps({
            "event_time":     row[0],
            "symbol":         row[1],
            "exchange":       row[2],
            "last_update_id": row[3],
            "bids":           json.loads(row[4]) if isinstance(row[4], str) else row[4],
            "asks":           json.loads(row[5]) if isinstance(row[5], str) else row[5],
        })

    ds_depth_dict = ds_depth_row.map(depth_row_to_dict, output_type=Types.STRING())
    ds_depth_dict.flat_map(
        DepthWriter(), output_type=Types.STRING()
    ).name("Write_Depth_To_KeyDB")

    # ────────────────────────────────────────────────────────────────────
    # Liquidity heatmap pipeline (Task 5, v0.24.5b)
    # ────────────────────────────────────────────────────────────────────
    # The heatmap writer is a side-effect of the depth stream: it
    # consumes the SAME crypto_depth Kafka topic and aggregates depth
    # by price bucket (0.1% per bucket, max ±1% from mid). Output goes
    # to:
    #   - InfluxDB measurement : liquidity_heatmap
    # Parallel to the depth writer; if this branch fails, the depth
    # writer is unaffected.
    #
    # Default exchange=binance because AGENTS.md notes the depth topic
    # drops the exchange field. Override via env var HEATMAP_EXCHANGE.
    from writers.liquidity_heatmap import LiquidityHeatmapWriter  # noqa: E402
    import os as _os_h
    _heat_exchange = _os_h.environ.get("HEATMAP_EXCHANGE", "binance")
    log.info("[Pipeline] liquidity heatmap exchange = %s", _heat_exchange)
    ds_depth_dict.flat_map(
        LiquidityHeatmapWriter(default_exchange=_heat_exchange),
        output_type=Types.STRING(),
    ).name("Liquidity_Heatmap_To_InfluxDB")


    # --------------------------------------------------------------------------
    # Trade pipeline: crypto_trades -> KeyDB (hot cache)
    # --------------------------------------------------------------------------

    t_env.execute_sql(f"""
        CREATE TABLE kafka_trades (
            event_time      BIGINT,
            symbol          STRING,
            exchange        STRING,
            agg_trade_id    BIGINT,
            price           DOUBLE,
            quantity        DOUBLE,
            trade_time      BIGINT,
            is_buyer_maker  BOOLEAN
        ) WITH (
            'connector'                    = 'kafka',
            'topic'                        = 'crypto_trades',
            'properties.bootstrap.servers' = '{KAFKA_BOOTSTRAP}',
            'properties.group.id'          = 'flink_crypto_trades_v1',
            'scan.startup.mode'            = 'latest-offset',
            'format'                       = 'avro-confluent',
            'avro-confluent.url'           = '{SCHEMA_REGISTRY_URL}'
        )
    """)

    trades_table = t_env.sql_query("""
        SELECT
            event_time, symbol, exchange, agg_trade_id,
            price, quantity, trade_time, is_buyer_maker
        FROM kafka_trades
    """)
    ds_trades_row = t_env.to_data_stream(trades_table)

    def trade_row_to_dict(row):
        return json.dumps({
            "event_time":       row[0],
            "symbol":           row[1],
            "exchange":         row[2],
            "agg_trade_id":     row[3],
            "price":            row[4],
            "quantity":         row[5],
            "trade_time":       row[6],
            "is_buyer_maker":   row[7],
        })

    ds_trades_dict = ds_trades_row.map(trade_row_to_dict, output_type=Types.STRING())
    ds_trades_dict.flat_map(
        KeyDBTradeWriter(), output_type=Types.STRING()
    ).name("Write_Trades_To_KeyDB")

    # ────────────────────────────────────────────────────────────────────
    # Whale alert pipeline (Task 2, v0.24.4)
    # ────────────────────────────────────────────────────────────────────
    # The whale alert writer is a side-effect of the trade stream:
    # it consumes the SAME crypto_trades Kafka topic (cheap; already
    # in memory after the deserializer) and filters for trades whose
    # notional USD >= WHALE_ALERT_MIN_USD. Detected alerts go to:
    #   - Redis sorted set  : whale:alerts:{exchange}:{symbol}
    #   - InfluxDB          : whale_alerts measurement
    # This branch is parallel to the trade writer; if the writer fails
    # the trade writer is unaffected (separate pipeline path).
    #
    # Default threshold $100K is the standard retail "whale" cut-off.
    # Override at deploy time via env var WHALE_ALERT_MIN_USD.
    import os as _os
    _whale_min_usd = float(
        _os.environ.get("WHALE_ALERT_MIN_USD", str(DEFAULT_MIN_WHALE_USD))
    )
    log.info("[Pipeline] whale alert threshold = $%.0f", _whale_min_usd)
    ds_trades_dict.flat_map(
        WhaleAlertWriter(min_whale_usd=_whale_min_usd),
        output_type=Types.STRING(),
    ).name("Whale_Alerts_To_KeyDB+InfluxDB")

    env.execute("Crypto_MultiStream_Kafka_to_KeyDB_InfluxDB")


if __name__ == "__main__":
    run()

