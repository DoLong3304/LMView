"""
Persistent state store for the indicator writer (B7 fix).

Bottleneck B7 — Flink aggregator state lost on restart
-----------------------------------------------------
``IndicatorWriter`` keeps five in-process dicts that hold the
rolling close / volume / candle deques and the EMA / MACD signal
state for every symbol. On a Flink restart those dicts come back
empty, forcing the writer to re-warm from a Kafka replay — a
multi-minute gap where the dashboard shows no indicator values.

The proper long-term answer is Flink's ``ValueState`` / ``ListState``
backed by RocksDB, but migrating a ``FlatMapFunction`` to a
``KeyedProcessFunction`` is a non-trivial refactor. As an
intermediate step we add a *write-through* layer:

  * On every emit, we write a small JSON snapshot of the per-symbol
    state to Redis under
    ``indicator:state:{exchange}:{symbol}`` with a 7-day TTL.
  * On ``open()`` (subtask start-up), we read the snapshot back
    and re-hydrate the in-process dicts.
  * When Flink restarts, the new subtask picks up where the old
    one left off — no replay required, warmup is ~1ms.

The class is deliberately synchronous (no async) because
``IndicatorWriter`` is a Flink operator and runs in a JVM-bound
Python worker that does not share an event loop with the
FastAPI app.
"""
from __future__ import annotations

import json
import logging
import os
import time
from collections import deque
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Default TTL for the persisted state key (7 days matches the
# existing ``INDICATOR_HISTORY_TTL_SEC`` default).
DEFAULT_STATE_TTL_SEC = int(os.environ.get("INDICATOR_STATE_TTL_SEC", "604800"))


class IndicatorStateStore:
    """Redis-backed write-through cache for indicator state.

    Args:
        redis_client: a ``redis.Redis`` (or sentinel-aware equivalent)
            client. We don't enforce a specific class here so the
            writer can keep using its existing ``get_flink_redis()``
            helper.
        ttl_sec: how long the snapshot lives in Redis. After the TTL
            a restarted writer will fall back to a Kafka replay for
            that key.
    """

    KEY_PREFIX = "indicator:state"

    def __init__(self, redis_client, ttl_sec: int = DEFAULT_STATE_TTL_SEC) -> None:
        self._r = redis_client
        self._ttl = ttl_sec
        # Counters used by tests + dashboards.
        from writers.metrics import (
            record_indicator_warmup,
            record_indicator_recompute,
        )
        self._record_warmup = record_indicator_warmup
        self._record_recompute = record_indicator_recompute

    # ── Keys ────────────────────────────────────────────────────────
    def _key(self, exchange: str, symbol: str) -> str:
        return f"{self.KEY_PREFIX}:{exchange}:{symbol}"

    # ── Persist ─────────────────────────────────────────────────────
    def save(self, exchange: str, symbol: str, payload: Dict[str, Any]) -> None:
        """Persist a snapshot of the per-symbol state.

        ``payload`` is a small JSON-serialisable dict. The size cap
        per key is ~256KB which is plenty for 60 closes + EMAs.
        """
        try:
            self._r.set(
                self._key(exchange, symbol),
                json.dumps(payload, separators=(",", ":")),
                ex=self._ttl,
            )
        except Exception as exc:
            # Never let a Redis hiccup kill the indicator pipeline.
            logger.warning("indicator state save failed (%s:%s): %s",
                           exchange, symbol, exc)

    def save_batch(self, exchange: str, payloads: Dict[str, Dict[str, Any]]) -> None:
        """Persist multiple symbols in a single pipeline.

        ``payloads`` is a {symbol: payload} dict; we group them under
        the same exchange prefix.
        """
        if not payloads:
            return
        try:
            pipe = self._r.pipeline(transaction=False)
            for symbol, payload in payloads.items():
                pipe.set(
                    self._key(exchange, symbol),
                    json.dumps(payload, separators=(",", ":")),
                    ex=self._ttl,
                )
            pipe.execute()
        except Exception as exc:
            logger.warning("indicator state batch save failed (exchange=%s): %s",
                           exchange, exc)

    # ── Hydrate ─────────────────────────────────────────────────────
    def load(self, exchange: str, symbol: str) -> Optional[Dict[str, Any]]:
        """Read the snapshot for a symbol, or ``None`` if missing.

        Used by ``IndicatorWriter.open()`` to repopulate its in-process
        deques without going back to Kafka.
        """
        try:
            raw = self._r.get(self._key(exchange, symbol))
        except Exception as exc:
            logger.warning("indicator state load failed (%s:%s): %s",
                           exchange, symbol, exc)
            return None
        if not raw:
            return None
        try:
            return json.loads(raw)
        except (TypeError, ValueError) as exc:
            logger.warning("indicator state corrupt for %s:%s: %s",
                           exchange, symbol, exc)
            return None

    def hydrate_writer(self, writer, exchange: str) -> int:
        """Repopulate ``writer``'s in-process state from Redis.

        ``writer`` is expected to expose the five dicts the
        ``IndicatorWriter`` keeps:

            _closes, _volumes, _candles,
            _ema_state, _macd_signal_state

        We discover the symbols to hydrate via ``SCAN`` of the
        state prefix so we don't need a separate index.

        Returns the number of symbols hydrated. Records the warmup
        duration via ``record_indicator_warmup`` (B7 observability).
        """
        start = time.monotonic()
        hydrated = 0
        pattern = f"{self.KEY_PREFIX}:{exchange}:*"
        try:
            # ``SCAN`` is preferred over ``KEYS`` because the latter
            # is O(N) and blocks the Redis event loop on a large keyspace.
            for key in self._r.scan_iter(match=pattern, count=500):
                # Key format: ``indicator:state:{exchange}:{symbol}``
                parts = key.split(":")
                if len(parts) < 4:
                    continue
                symbol = ":".join(parts[3:])
                payload = self.load(exchange, symbol)
                if payload is None:
                    continue
                self._apply_to_writer(writer, symbol, payload)
                hydrated += 1
        except Exception as exc:
            logger.warning("indicator hydrate failed (exchange=%s): %s",
                           exchange, exc)
        duration = time.monotonic() - start
        if hydrated > 0:
            self._record_warmup(state_type="candle_deque", duration_sec=duration)
            logger.info(
                "hydrated %d indicator state keys for exchange=%s in %.3fs",
                hydrated, exchange, duration,
            )
        return hydrated

    def _apply_to_writer(
        self,
        writer,
        symbol: str,
        payload: Dict[str, Any],
    ) -> None:
        """Apply a single payload to the writer's in-memory state."""
        max_history = getattr(writer, "MAX_HISTORY", 60)
        closes = payload.get("closes", [])
        if closes:
            writer._closes[symbol] = deque(closes, maxlen=max_history)
        volumes = payload.get("volumes", [])
        if volumes:
            writer._volumes[symbol] = deque(volumes, maxlen=max_history)
        candles = payload.get("candles", [])
        if candles:
            writer._candles[symbol] = deque(candles, maxlen=max_history)
        ema_state = payload.get("ema_state", {})
        if ema_state:
            # JSON returns str keys; convert back to int.
            writer._ema_state[symbol] = {int(k): v for k, v in ema_state.items()}
        macd_state = payload.get("macd_signal_state")
        if macd_state is not None:
            writer._macd_signal_state[symbol] = macd_state
        # ``indicator`` is a stable label; the dashboard is per-symbol
        # not per-recompute so we keep the label cardinality low.
        self._record_recompute(indicator="state_hydrate", trigger="hydrate")

    def snapshot_writer(self, writer) -> Dict[str, Dict[str, Any]]:
        """Build a {symbol: payload} dict from the writer's current
        in-process state. Call this after every emit to keep Redis
        in sync with memory."""
        snapshots: Dict[str, Dict[str, Any]] = {}
        for symbol in writer._closes.keys():
            closes = list(writer._closes.get(symbol, []))
            volumes = list(writer._volumes.get(symbol, []))
            candles = list(writer._candles.get(symbol, []))
            ema = writer._ema_state.get(symbol, {})
            macd = writer._macd_signal_state.get(symbol)
            if not (closes or volumes or candles or ema or macd is not None):
                continue
            snapshots[symbol] = {
                "closes": closes[-writer.MAX_HISTORY:],
                "volumes": volumes[-writer.MAX_HISTORY:],
                "candles": candles[-writer.MAX_HISTORY:],
                "ema_state": {str(k): v for k, v in ema.items()},
                "macd_signal_state": macd,
                "saved_at": time.time(),
            }
        return snapshots
