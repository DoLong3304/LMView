#!/usr/bin/env python3
"""
Exchange-agnostic Kafka producer service.

Spawns WebSocket stream threads for ticker, aggTrade, kline, and depth
data from any exchange implementing ``ExchangeClient``.  Currently wired
to Binance; adding a second source is a matter of instantiating another
client and calling ``run_streams()`` again.

Usage (Docker)::

    CMD ["python", "src/producer/main.py"]
"""

import json
import logging
import os
import random
import signal
import sys
import threading
import time
from typing import Any

from prometheus_client import Counter, Gauge, Histogram, start_http_server

# ── Ensure project root is on the path so shared modules are importable ──────
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import websocket

from common.config import (
    DEPTH_LEVEL,
    DEPTH_UPDATE_MS,
    ENABLE_DIRECT_REDIS,
    ENABLE_OKX,
    KAFKA_TOPIC_DEPTH,
    KAFKA_TOPIC_KLINES,
    KAFKA_TOPIC_TICKER,
    KAFKA_TOPIC_TRADES,
    KLINE_INTERVAL_WS,
    MAX_SYMBOLS,
    SCHEMA_REGISTRY_URL,
    SYMBOLS_PER_CONNECTION,
    SYMBOLS_PER_DEPTH_CONN,
    TICKER_HEARTBEAT_SEC,
)
from common.avro_serializer import AvroSerializer
from common.kafka_client import flush_and_close, init_producer, send_to_kafka
from common.logging import setup_logging
from exchanges.base import ExchangeClient
from exchanges.binance.client import BinanceClient
from exchanges.binance.redis_writer import get_direct_writer
from exchanges.okx.client import OKXClient
from producer.health_monitor import HealthMonitor
from producer.metrics import (
    DEDUP_DUPLICATES_SKIPPED,
    DEDUP_MESSAGES_FORWARDED,
    DEDUP_STATE_SIZE,
    EXCHANGE_MESSAGES_RECEIVED,
    EXCHANGE_WS_CONNECTED,
    HEARTBEAT_TIMESTAMP as PROD_HEARTBEAT,
    RECONNECT_BACKOFF_SECONDS,
    init_metrics,
    record_dedup_decision,
    record_exchange_message,
    record_exchange_ws_state,
    record_reconnect_backoff,
)

log = logging.getLogger(__name__)

# ── Per-symbol dedup state for ticker throttling ─────────────────────────────
# B1 fix (race condition): the dicts are read+written from multiple
# WebSocket threads. The compound check-then-set in ``handle_ticker_message``
# is not atomic under Python's GIL when more than one statement touches
# the dict, so we wrap all access in a single ``threading.Lock``. The
# critical section is short (a few dict reads and writes) so contention
# is negligible compared to the network round-trip that follows.
import threading
_dedup_lock = threading.Lock()
_last_close: dict[str, float] = {}
_last_sent_ts: dict[str, float] = {}

avro_serializer: AvroSerializer | None = None
health_monitor = HealthMonitor()

# ── Prometheus metrics ────────────────────────────────────────────────────────
WS_THREADS_RUNNING = Gauge(
    "producer_ws_threads_running",
    "Number of WebSocket threads currently running",
)
KAFKA_MESSAGES_SENT = Counter(
    "producer_kafka_messages_sent_total",
    "Total Kafka messages sent by topic",
    ["topic"],
)
KAFKA_SEND_ERRORS = Counter(
    "producer_kafka_send_errors_total",
    "Total Kafka send errors",
    ["topic"],
)
# HEARTBEAT_TIMESTAMP is defined in producer.metrics and re-exported from
# there to keep all producer-level Prometheus metrics in a single place.
WS_RECONNECT_COUNT = Counter(
    "producer_ws_reconnects_total",
    "Total WebSocket reconnection attempts",
    ["stream"],
)
TICKER_THROTTLE_SKIPPED = Counter(
    "producer_ticker_throttle_skipped_total",
    "Total ticker messages skipped due to throttle",
)


def _heartbeat(name: str) -> None:
    health_monitor.heartbeat(name)
    HEARTBEAT_TIMESTAMP.labels(thread=name).set(time.time())


def _compute_backoff(base_delay: float, attempt: int, max_delay: float = 60.0) -> float:
    delay = min(max_delay, base_delay * (2 ** min(attempt, 5)))
    jitter = delay * (0.25 * random.random())
    return delay + jitter


# ═══════════════════════════════════════════════════════════════════════════════
# Generic stream runners (exchange-agnostic)
# ═══════════════════════════════════════════════════════════════════════════════

def handle_ticker_message(message: str, client: ExchangeClient) -> None:
    """Process a batch ticker update, applying change+heartbeat throttle."""
    try:
        batch: list[dict[str, Any]] = json.loads(message)
    except json.JSONDecodeError as e:
        log.error("Ticker JSON decode error: %s", e)
        return

    if not isinstance(batch, list):
        return

    now = time.monotonic()
    sent_change = sent_heartbeat = skipped = 0
    exchange_name = getattr(client, "name", "unknown")

    record_exchange_message(exchange=exchange_name, stream="ticker", n=len(batch))

    for raw in batch:
        symbol = raw.get("s", "")
        if not symbol.endswith("USDT"):
            continue

        cur = float(raw.get("c", 0))
        # B1 fix: take the lock for the entire check-then-set so two
        # threads cannot both decide to forward the same symbol's update
        # when the price changed between their reads.
        with _dedup_lock:
            price_changed = _last_close.get(symbol) != cur
            heartbeat_due = (now - _last_sent_ts.get(symbol, 0)) >= TICKER_HEARTBEAT_SEC

            if not price_changed and not heartbeat_due:
                skipped += 1
                continue

            _last_close[symbol] = cur
            _last_sent_ts[symbol] = now
        try:
            send_to_kafka(KAFKA_TOPIC_TICKER, client.map_ticker(raw), avro_serializer)
            KAFKA_MESSAGES_SENT.labels(topic=KAFKA_TOPIC_TICKER).inc()
        except Exception as e:
            KAFKA_SEND_ERRORS.labels(topic=KAFKA_TOPIC_TICKER).inc()
            log.error("[TICKER] Kafka send error: %s", e)

        # Direct Redis bypass (auto-enabled when Kafka/Flink down)
        destination = "kafka"
        if health_monitor.is_direct_redis_active():
            try:
                direct_writer = get_direct_writer()
                mapped = client.map_ticker(raw)
                direct_writer.write_ticker("binance", mapped.get("symbol", ""), mapped)
                destination = "direct_redis"
            except Exception as e:
                log.error("[DirectRedis/ticker] write error: %s", e)

        if price_changed:
            sent_change += 1
        else:
            sent_heartbeat += 1

    total_sent = sent_change + sent_heartbeat
    if total_sent > 0:
        log.info(
            "[TICKER] sent=%d (change=%d, heartbeat=%d), skipped=%d",
            total_sent, sent_change, sent_heartbeat, skipped,
        )
    if skipped > 0:
        TICKER_THROTTLE_SKIPPED.inc(skipped)

    # New extended metrics: track dedup decisions per exchange
    record_dedup_decision(
        exchange=exchange_name,
        skipped=skipped,
        forwarded=total_sent,
        destination=destination,
    )
    DEDUP_STATE_SIZE.set(len(_last_close))


def run_ticker_stream(client: ExchangeClient) -> None:
    """Connect to the all-ticker WebSocket and stream indefinitely."""
    url = client.build_ticker_stream_url()
    attempt = 0
    worker_name = threading.current_thread().name
    exchange_name = getattr(client, "name", "unknown")
    while True:
        _heartbeat(worker_name)
        try:
            ws = websocket.WebSocketApp(
                url,
                on_open=lambda ws: (
                    log.info("[TICKER] WebSocket opened."),
                    record_exchange_ws_state(exchange=exchange_name, stream="ticker", connected=True),
                ),
                on_message=lambda ws, msg: handle_ticker_message(msg, client),
                on_error=lambda ws, err: log.error("[TICKER] Error: %s", err),
                on_close=lambda ws, code, msg: (
                    log.warning("[TICKER] Closed. code=%s msg=%s", code, msg),
                    record_exchange_ws_state(exchange=exchange_name, stream="ticker", connected=False),
                ),
            )
            log.info("[TICKER] Connecting to %s", url)
            ws.run_forever(ping_interval=40, ping_timeout=30, reconnect=0)
            attempt += 1
            delay = _compute_backoff(1.0, attempt)
            log.warning("[TICKER] Dropped. Reconnecting in %.1fs...", delay)
            WS_RECONNECT_COUNT.labels(stream="ticker").inc()
            record_reconnect_backoff(exchange=exchange_name, stream="ticker", sleep_sec=delay)
            time.sleep(delay)
        except Exception as e:
            attempt += 1
            delay = _compute_backoff(1.0, attempt)
            log.exception("[TICKER] Unexpected error: %s. Retry in %.1fs...", e, delay)
            time.sleep(delay)


def _handle_combined_message(
    message: str,
    event_type: str,
    mapper,
    topic: str,
    tag: str,
) -> None:
    """Generic handler for combined-stream WebSocket messages."""
    try:
        envelope: Any = json.loads(message)
    except json.JSONDecodeError as e:
        log.error("[%s] JSON decode error: %s", tag, e)
        return

    if not isinstance(envelope, dict):
        return

    payload = envelope.get("data", envelope)

    if event_type == "depth":
        # Partial book depth uses different event type / structure
        if not isinstance(payload, dict) or "lastUpdateId" not in payload:
            if isinstance(payload, dict) and payload.get("e") != "depthUpdate":
                return
        # For combined streams, symbol comes from the stream name
        if "s" not in payload:
            stream_name = envelope.get("stream", "")
            symbol = stream_name.split("@")[0].upper() if stream_name else ""
            payload["s"] = symbol
        symbol = str(payload.get("s", "")).upper()
        payload["s"] = symbol
    else:
        if not isinstance(payload, dict) or payload.get("e") != event_type:
            return
        symbol = payload.get("s", "")

    if not symbol.endswith("USDT"):
        return

    try:
        send_to_kafka(topic, mapper(payload), avro_serializer)
        KAFKA_MESSAGES_SENT.labels(topic=topic).inc()
    except Exception as e:
        KAFKA_SEND_ERRORS.labels(topic=topic).inc()
        log.error("[%s] Kafka send error: %s", tag, e)

    # Direct Redis bypass
    if ENABLE_DIRECT_REDIS:
        try:
            direct_writer = get_direct_writer()
            mapped = mapper(payload)
            if event_type == "aggTrade":
                direct_writer.write_trade("binance", symbol, mapped)
            elif event_type == "kline":
                interval = KLINE_INTERVAL_WS
                mapped["kline_start"] = payload.get("k", {}).get("t", 0) if isinstance(payload.get("k"), dict) else 0
                mapped["open"] = float(mapped.get("open", 0))
                mapped["high"] = float(mapped.get("high", 0))
                mapped["low"] = float(mapped.get("low", 0))
                mapped["close"] = float(mapped.get("close", 0))
                mapped["volume"] = float(mapped.get("volume", 0))
                mapped["quote_volume"] = float(mapped.get("quote_volume", 0))
                mapped["trade_count"] = int(mapped.get("trade_count", 0))
                mapped["is_closed"] = bool(mapped.get("is_closed", False))
                direct_writer.write_kline("binance", symbol, interval, mapped)
            elif event_type == "depth":
                direct_writer.write_depth("binance", symbol, payload)
        except Exception as e:
            log.error("[DirectRedis/%s] write error: %s", tag, e)

    log.debug("[%s] %s processed", tag, symbol)


# ?? OKX subscription-frame message handler ?????????????????????????????????
def _handle_okx_message(
    message: str,
    client,
    tag: str,
) -> None:
    """Handle OKX subscription-frame response messages.

    OKX format: {"arg":{"channel":"trades","instId":"BTC-USDT"}, "data":[...]}

    Dispatches to the correct mapper based on ``arg.channel``.
    """
    try:
        envelope = json.loads(message)
    except json.JSONDecodeError:
        return

    if not isinstance(envelope, dict):
        return

    arg = envelope.get("arg", {}) if isinstance(envelope.get("arg"), dict) else {}
    data = envelope.get("data", [])
    event = envelope.get("event", "")

    # Skip subscribe/unsubscribe confirmations
    if event in ("subscribe", "unsubscribe", "error"):
        if event == "error":
            log.error("[OKX/%s] Error: code=%s msg=%s",
                      tag, envelope.get("code"), envelope.get("msg"))
        return

    if not data or not isinstance(data, list):
        return

    channel = arg.get("channel", "")
    inst_id_raw = arg.get("instId", "")
    symbol = inst_id_raw.replace("-", "").upper()

    if not symbol.endswith("USDT"):
        return

    if channel == "tickers":
        for item in data:
            item["instId"] = inst_id_raw
            try:
                send_to_kafka(KAFKA_TOPIC_TICKER, client.map_ticker(item), avro_serializer)
                KAFKA_MESSAGES_SENT.labels(topic=KAFKA_TOPIC_TICKER).inc()
            except Exception as e:
                KAFKA_SEND_ERRORS.labels(topic=KAFKA_TOPIC_TICKER).inc()
                log.error("[OKX/TICKER] Kafka send error: %s", e)

            # Direct Redis bypass
            if ENABLE_DIRECT_REDIS:
                try:
                    direct_writer = get_direct_writer()
                    mapped = client.map_ticker(item)
                    direct_writer.write_ticker("okx", symbol, mapped)
                except Exception as e:
                    log.error("[DirectRedis/OKX-ticker] write error: %s", e)

    elif channel == "trades":
        for item in data:
            item["instId"] = inst_id_raw
            try:
                send_to_kafka(KAFKA_TOPIC_TRADES, client.map_trade(item), avro_serializer)
                KAFKA_MESSAGES_SENT.labels(topic=KAFKA_TOPIC_TRADES).inc()
            except Exception as e:
                KAFKA_SEND_ERRORS.labels(topic=KAFKA_TOPIC_TRADES).inc()
                log.error("[OKX/TRADES] Kafka send error: %s", e)

            # Direct Redis bypass
            if ENABLE_DIRECT_REDIS:
                try:
                    direct_writer = get_direct_writer()
                    mapped = client.map_trade(item)
                    direct_writer.write_trade("okx", symbol, mapped)
                except Exception as e:
                    log.error("[DirectRedis/OKX-trade] write error: %s", e)

    elif channel.startswith("candle"):
        for item in data:
            mapped = client.map_kline(item)
            mapped["symbol"] = symbol
            try:
                send_to_kafka(KAFKA_TOPIC_KLINES, mapped, avro_serializer)
                KAFKA_MESSAGES_SENT.labels(topic=KAFKA_TOPIC_KLINES).inc()
            except Exception as e:
                KAFKA_SEND_ERRORS.labels(topic=KAFKA_TOPIC_KLINES).inc()
                log.error("[OKX/KLINES] Kafka send error: %s", e)

            # Direct Redis bypass
            if ENABLE_DIRECT_REDIS:
                try:
                    direct_writer = get_direct_writer()
                    interval = channel.replace("candle", "")
                    mapped["kline_start"] = int(item[0]) if isinstance(item, list) and item else 0
                    mapped["open"] = float(item[1]) if isinstance(item, list) and len(item) > 1 else 0
                    mapped["high"] = float(item[2]) if isinstance(item, list) and len(item) > 2 else 0
                    mapped["low"] = float(item[3]) if isinstance(item, list) and len(item) > 3 else 0
                    mapped["close"] = float(item[4]) if isinstance(item, list) and len(item) > 4 else 0
                    mapped["volume"] = float(item[5]) if isinstance(item, list) and len(item) > 5 else 0
                    mapped["quote_volume"] = float(item[6]) if isinstance(item, list) and len(item) > 6 else 0
                    direct_writer.write_kline("okx", symbol, interval, mapped)
                except Exception as e:
                    log.error("[DirectRedis/OKX-kline] write error: %s", e)

    elif channel.startswith("books"):
        for item in data:
            mapped = client.map_depth(item)
            mapped["symbol"] = symbol
            try:
                send_to_kafka(KAFKA_TOPIC_DEPTH, mapped, avro_serializer)
                KAFKA_MESSAGES_SENT.labels(topic=KAFKA_TOPIC_DEPTH).inc()
            except Exception as e:
                KAFKA_SEND_ERRORS.labels(topic=KAFKA_TOPIC_DEPTH).inc()
                log.error("[OKX/DEPTH] Kafka send error: %s", e)

            # Direct Redis bypass
            if ENABLE_DIRECT_REDIS:
                try:
                    direct_writer = get_direct_writer()
                    direct_writer.write_depth("okx", symbol, item)
                except Exception as e:
                    log.error("[DirectRedis/OKX-depth] write error: %s", e)


def run_ticker_stream_subscription(client) -> None:
    """Connect to OKX public WS, subscribe to all-tickers on open."""
    url = client.build_ticker_stream_url()
    symbols = client.fetch_symbols()[:MAX_SYMBOLS]

    # Filter to well-known USDT pairs that definitely trade on OKX
    well_known = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
                  "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "MATICUSDT",
                  "LINKUSDT", "SHIBUSDT", "LTCUSDT", "ATOMUSDT", "UNICUSDT",
                  "XLMUSDT", "VETUSDT", "ICPUSDT", "FILUSDT", "AAVEUSDT"]
    symbols = [s for s in symbols if s in well_known]

    if not symbols:
        log.warning("[OKX/TICKER] No valid symbols to subscribe")
        return

    channels = client.build_ticker_channels(symbols)

    # Batch channels into groups of ~50
    for offset in range(0, len(channels), 50):
        batch = channels[offset:offset + 50]
        frame = client.build_subscribe_frame(batch, "subscribe")
        attempt = 0

        while True:
            try:
                _heartbeat(threading.current_thread().name)
                ws = websocket.WebSocketApp(
                    url,
                    on_open=lambda ws, f=frame: ws.send(f),
                    on_message=lambda ws, msg: _handle_okx_message(msg, client, "TICKER"),
                    on_error=lambda ws, err: log.error("[OKX/TICKER] Error: %s", err),
                    on_close=lambda ws, code, msg: log.warning(
                        "[OKX/TICKER] Closed. code=%s msg=%s", code, msg),
                )
                log.info("[OKX/TICKER] Connecting to %s (batch %d channels)", url, len(batch))
                ws.run_forever(ping_interval=25, ping_timeout=20, reconnect=0)
                attempt += 1
                delay = _compute_backoff(1.0, attempt)
                log.warning("[OKX/TICKER] Dropped. Reconnecting in %.1fs...", delay)
                time.sleep(delay)
            except Exception as e:
                attempt += 1
                delay = _compute_backoff(1.0, attempt)
                log.exception("[OKX/TICKER] Unexpected error: %s. Retry in %.1fs...", e, delay)
                time.sleep(delay)


def run_combined_batch_subscription(
    client,
    symbols_batch: list[str],
    batch_idx: int,
    channel_type: str,
    tag: str,
) -> None:
    """Run an OKX subscription-based WebSocket for a batch of symbols.

    channel_type: "trades", "kline", or "depth"
    """
    url = client.build_combined_stream_url([])  # same WS URL, subscription via frame
    # OKX uses 1m minimum for klines (doesn't support 1s)
    interval = "1m" if channel_type == "kline" else None
    depth_level = DEPTH_LEVEL if channel_type == "depth" else None

    # Build channels
    if channel_type == "trades":
        channels = client.build_trade_channels(symbols_batch)
    elif channel_type == "kline":
        channels = client.build_kline_channels(symbols_batch, interval)
    elif channel_type == "depth":
        channels = client.build_depth_channels(symbols_batch, str(depth_level))
    else:
        return

    frame = client.build_subscribe_frame(channels, "subscribe")

    attempt = 0
    while True:
        try:
            _heartbeat(threading.current_thread().name)
            ws = websocket.WebSocketApp(
                url,
                on_open=lambda ws, f=frame: ws.send(f),
                on_message=lambda ws, msg: _handle_okx_message(msg, client, tag),
                on_error=lambda ws, err: log.error("[OKX/%s] Batch %d error: %s", tag, batch_idx, err),
                on_close=lambda ws, code, msg: log.warning(
                    "[OKX/%s] Batch %d closed. code=%s", tag, batch_idx, code),
            )
            log.info("[OKX/%s] Batch %d connecting (%d channels)", tag, batch_idx, len(channels))
            ws.run_forever(ping_interval=25, ping_timeout=20, reconnect=0)
            attempt += 1
            delay = _compute_backoff(1.0 + batch_idx, attempt)
            log.warning("[OKX/%s] Batch %d dropped. Reconnecting in %.1fs...", tag, batch_idx, delay)
            time.sleep(delay)
        except Exception as e:
            attempt += 1
            delay = _compute_backoff(1.0 + batch_idx, attempt)
            log.exception("[OKX/%s] Batch %d error: %s. Retry in %.1fs...", tag, batch_idx, e, delay)
            time.sleep(delay)


def run_combined_batch(
    stream_url: str,
    batch_idx: int,
    event_type: str,
    mapper,
    topic: str,
    tag: str,
) -> None:
    """Run a combined-stream WebSocket with auto-reconnect."""
    url_preview = stream_url[:120] + "..." if len(stream_url) > 120 else stream_url
    attempt = 0
    while True:
        try:
            _heartbeat(threading.current_thread().name)
            ws = websocket.WebSocketApp(
                stream_url,
                on_open=lambda ws: log.info("[%s] Batch #%d WebSocket opened.", tag, batch_idx),
                on_message=lambda ws, msg: _handle_combined_message(
                    msg, event_type, mapper, topic, tag
                ),
                on_error=lambda ws, err: log.error("[%s] Batch #%d error: %s", tag, batch_idx, err),
                on_close=lambda ws, code, msg: log.warning(
                    "[%s] Batch #%d closed. code=%s", tag, batch_idx, code
                ),
            )
            log.info("[%s] Batch #%d connecting: %s", tag, batch_idx, url_preview)
            ws.run_forever(ping_interval=40, ping_timeout=30, reconnect=0)
            attempt += 1
            delay = _compute_backoff(1.0 + batch_idx, attempt)
            log.warning("[%s] Batch #%d dropped. Reconnecting in %.1fs...", tag, batch_idx, delay)
            time.sleep(delay)
        except Exception as e:
            attempt += 1
            delay = _compute_backoff(1.0 + batch_idx, attempt)
            log.exception("[%s] Batch #%d unexpected error: %s. Retry in %.1fs...", tag, batch_idx, e, delay)
            time.sleep(delay)


def _start_thread(name: str, target, *args) -> threading.Thread:
    thread = threading.Thread(target=target, args=args, daemon=True, name=name)
    thread.start()
    health_monitor.attach_thread(name, thread)
    WS_THREADS_RUNNING.inc()
    return thread


def _register_thread(name: str, target, *args) -> None:
    health_monitor.register(name, lambda: _start_thread(name, target, *args))
    _start_thread(name, target, *args)


# ═══════════════════════════════════════════════════════════════════════════════
# Main orchestrator
# ═══════════════════════════════════════════════════════════════════════════════

def run_streams(client: ExchangeClient) -> None:
    """Spawn all WebSocket stream threads for a given exchange client."""
    is_subscription = hasattr(client, "uses_subscription_frames") and client.uses_subscription_frames
    symbols = client.fetch_symbols()[:MAX_SYMBOLS]

    # For OKX, filter to well-known pairs and adjust interval
    kline_interval = KLINE_INTERVAL_WS
    if is_subscription:
        well_known = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
                      "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "MATICUSDT",
                      "LINKUSDT", "SHIBUSDT", "LTCUSDT", "ATOMUSDT", "UNICUSDT",
                      "XLMUSDT", "VETUSDT", "ICPUSDT", "FILUSDT", "AAVEUSDT"]
        symbols = [s for s in symbols if s in well_known]
        # OKX doesn't support 1s klines, use 1m minimum
        if KLINE_INTERVAL_WS == "1s":
            kline_interval = "1m"
        log.info("OKX filtered to %d well-known symbols, using %s kline interval", len(symbols), kline_interval)

    # ── Stream A: All-ticker ─────────────────────────────────────────────────
    ticker_name = f"{client.__class__.__name__.lower()}-ws-ticker"
    ticker_target = run_ticker_stream_subscription if is_subscription else run_ticker_stream
    _register_thread(ticker_name, ticker_target, client)

    # ── Stream B: Aggregate trades ───────────────────────────────────────────
    batches = [
        symbols[i : i + SYMBOLS_PER_CONNECTION]
        for i in range(0, len(symbols), SYMBOLS_PER_CONNECTION)
    ]
    log.info("Spawning %d aggTrade thread(s) for %d symbols (%d/connection).",
             len(batches), len(symbols), SYMBOLS_PER_CONNECTION)

    for idx, batch in enumerate(batches):
        streams = [client.trade_stream_name(s) for s in batch]
        url = client.build_combined_stream_url(streams)
        if is_subscription:
            _register_thread(
                f"{client.__class__.__name__.lower()}-ws-trades-{idx + 1}",
                run_combined_batch_subscription,
                client,
                batch,
                idx + 1,
                "trades",
                "TRADES",
            )
        else:
            _register_thread(
                f"{client.__class__.__name__.lower()}-ws-trades-{idx + 1}",
                run_combined_batch,
                url,
                idx + 1,
                "aggTrade",
                client.map_trade,
                KAFKA_TOPIC_TRADES,
                "TRADES",
            )
        time.sleep(1.0)

    # ── Stream C: Kline candles ──────────────────────────────────────────────
    log.info("Spawning %d kline thread(s) (interval=%s).", len(batches), kline_interval)
    for idx, batch in enumerate(batches):
        streams = [client.kline_stream_name(s, kline_interval) for s in batch]
        url = client.build_combined_stream_url(streams)
        if is_subscription:
            _register_thread(
                f"{client.__class__.__name__.lower()}-ws-klines-{idx + 1}",
                run_combined_batch_subscription,
                client,
                batch,
                idx + 1,
                "kline",
                "KLINES",
            )
        else:
            _register_thread(
                f"{client.__class__.__name__.lower()}-ws-klines-{idx + 1}",
                run_combined_batch,
                url,
                idx + 1,
                "kline",
                client.map_kline,
                KAFKA_TOPIC_KLINES,
                "KLINES",
            )
        time.sleep(1.0)

    # ── Stream D: Order-book depth ───────────────────────────────────────────
    depth_batches = [
        symbols[i : i + SYMBOLS_PER_DEPTH_CONN]
        for i in range(0, len(symbols), SYMBOLS_PER_DEPTH_CONN)
    ]
    log.info("Spawning %d depth thread(s) (@depth%s@%sms).",
             len(depth_batches), DEPTH_LEVEL, DEPTH_UPDATE_MS)
    if is_subscription:
        for idx, batch in enumerate(depth_batches):
            _register_thread(
                f"{client.__class__.__name__.lower()}-ws-depth-{idx + 1}",
                run_combined_batch_subscription,
                client,
                batch,
                idx + 1,
                "depth",
                "DEPTH",
            )
            time.sleep(1.0)
    else:
        for idx, batch in enumerate(depth_batches):
            streams = [client.depth_stream_name(s, DEPTH_LEVEL, DEPTH_UPDATE_MS) for s in batch]
            url = client.build_combined_stream_url(streams)
            _register_thread(
                f"{client.__class__.__name__.lower()}-ws-depth-{idx + 1}",
                run_combined_batch,
                url,
                idx + 1,
                "depth",
                client.map_depth,
                KAFKA_TOPIC_DEPTH,
                "DEPTH",
            )
            time.sleep(1.0)


def run() -> None:
    """Main entry point."""
    setup_logging("producer")

    log.info("=" * 60)
    log.info("Multi-Exchange Producer starting...")
    log.info("  → Stream A: !ticker@arr                    → topic: %s", KAFKA_TOPIC_TICKER)
    log.info("  → Stream B: @aggTrade                      → topic: %s", KAFKA_TOPIC_TRADES)
    log.info("  → Stream C: @kline_%s                    → topic: %s", KLINE_INTERVAL_WS, KAFKA_TOPIC_KLINES)
    log.info("  → Stream D: @depth%s@%sms               → topic: %s", DEPTH_LEVEL, DEPTH_UPDATE_MS, KAFKA_TOPIC_DEPTH)
    log.info("=" * 60)

    # ── Initialize Kafka producer ────────────────────────────────────────────
    # Prometheus metrics endpoint
    metrics_port = int(os.getenv("PRODUCER_METRICS_PORT", "9090"))
    start_http_server(metrics_port)
    log.info("Prometheus metrics server started on :%d", metrics_port)

    # Start a second metrics endpoint on a dedicated port for the extended
    # Prometheus job (config/prometheus.yml 'producer-extended' scrape job).
    try:
        extended_port = int(os.getenv("PRODUCER_EXT_METRICS_PORT", "9091"))
        if extended_port != metrics_port:
            start_http_server(extended_port)
            log.info("Producer extended metrics on :%d", extended_port)
    except OSError as e:
        log.warning("Could not bind extended metrics port: %s", e)

    # Initialise extended metrics gauges
    init_metrics()

    init_producer()

    # ── Register Avro schemas ────────────────────────────────────────────────
    global avro_serializer
    schema_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "..", "..", "schemas")
    avro_serializer = AvroSerializer(SCHEMA_REGISTRY_URL)
    avro_serializer.register(KAFKA_TOPIC_TICKER, os.path.join(schema_dir, "ticker.avsc"))
    avro_serializer.register(KAFKA_TOPIC_KLINES, os.path.join(schema_dir, "kline.avsc"))
    avro_serializer.register(KAFKA_TOPIC_TRADES, os.path.join(schema_dir, "trade.avsc"))
    avro_serializer.register(KAFKA_TOPIC_DEPTH,  os.path.join(schema_dir, "depth.avsc"))
    log.info("All Avro schemas registered.")

    # ── Start streams for Binance ────────────────────────────────────────────
    log.info("Starting Binance streams...")
    binance = BinanceClient()
    run_streams(binance)

    # ── Start streams for OKX (Active-Active HA) ─────────────────────────────
    if ENABLE_OKX:
        log.info("Starting OKX streams (Active-Active HA)...")
        okx = OKXClient()
        run_streams(okx)
    else:
        log.info("OKX streams disabled (set ENABLE_OKX=true to enable experimental source).")
    health_monitor.start_daemon()

    # ── Block main thread until shutdown ─────────────────────────────────────
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Received interrupt signal. Breaking main loop...")
    finally:
        log.info("Shutting down: flushing Kafka producer buffer...")
        flush_and_close()
        log.info("Shutdown complete.")


def _handle_sigterm(signum: int, frame: Any) -> None:
    log.info("SIGTERM received, initiating graceful shutdown...")
    raise KeyboardInterrupt


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _handle_sigterm)
    run()
