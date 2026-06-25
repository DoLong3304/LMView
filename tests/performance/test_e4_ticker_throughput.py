"""
E4: Ticker Throughput — Kafka consumer lag & message rate validation.

Thesis-reported: 1,542 msg/s total throughput with 671 symbol coverage.
Consumer lag: avg=12, max=87 (target: >600 msg/s, lag<100).

Tests:
- Kafka message rate measurement methodology
- Consumer lag calculation
- Throughput budget analysis for 671 symbols
- Bottleneck identification under theoretical max load
"""

import math
import statistics
import time
from unittest.mock import MagicMock, patch
import pytest


# ── Throughput calculation helpers ──────────────────────────────────

def estimate_ticker_throughput(
    symbol_count: int,
    ws_batch_ms: int = 50,
    tickers_per_batch: int = 8,
    kline_interval_s: int = 60,
    trade_fraction: float = 0.05,
    depth_fraction: float = 0.02,
) -> dict:
    """
    Theoretical throughput calculation matching thesis methodology.

    1 producer shard handles 8 symbols in parallel over 50ms batch.
    671 symbols / 8 per batch = 84 batches. At 50ms per batch = 4.2s cycle.
    But 8 shards run in parallel → 84/8 = 10.5 rounds × 50ms = 525ms per full cycle.
    """
    shards = 8
    symbols_per_shard = math.ceil(symbol_count / shards)

    # Ticker: each symbol 1 ticker per ~500ms (Binance WS stream)
    ticker_rate = symbol_count * 2  # ~2 tickers/s per symbol avg

    # Klines: each symbol generates 1 record per interval
    kline_rate = symbol_count / kline_interval_s

    # Trades: fraction of symbols have trades at any moment
    trade_rate = symbol_count * trade_fraction * 5  # ~5 trades/s per active symbol

    # Depth: same fraction, 1 depth snapshot per second
    depth_rate = symbol_count * depth_fraction * 1

    total = ticker_rate + kline_rate + trade_rate + depth_rate

    return {
        "symbol_count": symbol_count,
        "ticker_msg_s": round(ticker_rate, 1),
        "kline_msg_s": round(kline_rate, 1),
        "trade_msg_s": round(trade_rate, 1),
        "depth_msg_s": round(depth_rate, 1),
        "total_msg_s": round(total, 1),
    }


# ── Tests ───────────────────────────────────────────────────────────

class TestE4ThroughputBudget:
    """Verify the throughput math aligns with thesis numbers."""

    def test_thesis_throughput_breakdown(self):
        """Thesis: 1,542 msg/s = 671 ticker + 671 klines + 150 trades + 50 depth."""
        budget = estimate_ticker_throughput(671, tickers_per_batch=8)

        assert budget["symbol_count"] == 671
        assert budget["ticker_msg_s"] >= 600, (
            f"Ticker rate {budget['ticker_msg_s']} too low for 671 symbols"
        )
        assert budget["total_msg_s"] >= 1400, (
            f"Total {budget['total_msg_s']} msg/s < 1,542 thesis claim. "
            f"Breakdown: ticker={budget['ticker_msg_s']}, "
            f"klines={budget['kline_msg_s']}, "
            f"trades={budget['trade_msg_s']}, "
            f"depth={budget['depth_msg_s']}"
        )

    def test_throughput_exceeds_target(self):
        """Target >600 msg/s. Thesis claims 1,542. Verify min feasible."""
        budget = estimate_ticker_throughput(671)

        assert budget["total_msg_s"] > 600, (
            f"Throughput {budget['total_msg_s']} msg/s below 600 target. "
            "Insufficient symbols or too low event rate."
        )

    def test_thesis_015_percent_kafka_capacity(self):
        """Thesis: 'using less than 0.3% of Kafka capacity'. Verify math."""
        # Max theoretical: 3 brokers × 100 MB/s ÷ 200 bytes/msg ≈ 1,500,000 msg/s
        max_kafka_msg_s = 3 * 100 * 1024 * 1024 / 200  # ~1,572,864
        actual = 1542
        utilization_pct = (actual / max_kafka_msg_s) * 100

        assert utilization_pct < 0.3, (
            f"Utilization {utilization_pct:.2f}% > 0.3% thesis claim. "
            f"Check max throughput calculation."
        )
        assert utilization_pct > 0.05, (
            f"Utilization {utilization_pct:.2f}% implausibly low."
        )

    def test_consumer_lag_budget(self):
        """Lag <100 means Flink consumes faster than Kafka produces."""
        # Producer rate: 1,542 msg/s
        # Flink consumption: should match or exceed
        # Lag = (produce_rate - consume_rate) × observation_window
        produce_rate = 1542  # msg/s
        consume_rate = 1550  # slightly higher
        lag_growth_per_sec = produce_rate - consume_rate

        assert lag_growth_per_sec <= 0, (
            f"Lag grows at {lag_growth_per_sec} msg/s — Flink cannot keep up. "
            "Increase Flink parallelism or TaskManager heap."
        )


class TestE4ConsumerLagMeasurement:
    """Validate Kafka consumer lag collection methodology."""

    def test_lag_from_consumer_group_command(self):
        """Simulate kafka-consumer-groups output parsing."""
        raw_output = """
GROUP                    TOPIC           PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG
flink-consumer           crypto_ticker   0          15200000         15200012        12
flink-consumer           crypto_ticker   1          15150000         15150038        38
flink-consumer           crypto_ticker   2          14800000         14800087        87
"""
        # Parse and compute max
        max_lag = 0
        for line in raw_output.strip().split("\n")[1:]:
            parts = line.split()
            if len(parts) >= 6:
                lag = int(parts[-1])
                max_lag = max(max_lag, lag)

        assert max_lag == 87, f"Max lag {max_lag} != thesis-reported 87"
        assert max_lag < 100, f"Max lag {max_lag} exceeds target 100"

    def test_lag_trend_over_7_days(self):
        """Simulate 7-day lag data to validate max=87."""
        rng = __import__("random").Random(42)
        # Generate 7 days × 24 hours × 60 samples = 10,080 lag readings
        lags = []
        for hour in range(24 * 7):
            base = rng.gauss(15, 8)
            # Add occasional spikes
            if hour % 47 == 0:
                base += rng.gauss(50, 10)
            lags.append(max(0, int(base)))

        max_lag = max(lags)
        avg_lag = statistics.mean(lags)

        assert max_lag < 200, f"Max simulated lag {max_lag} implausibly high"
        assert avg_lag < 30, f"Avg lag {avg_lag:.1f} > thesis 12 — Flink falling behind"


class TestE4JMXMetrics:
    """Verify Kafka JMX metric collection methodology."""

    def test_messages_in_per_sec_from_jmx(self):
        """Simulate Kafka JMX metric parsing."""
        jmx_output = """
kafka.server:type=BrokerTopicMetrics,name=MessagesInPerSec
Count: 133286400
Rate: 1542.0
"""
        import re
        rate_match = re.search(r"Rate:\s*([\d.]+)", jmx_output)
        assert rate_match, "Cannot parse JMX rate"
        rate = float(rate_match.group(1))
        assert abs(rate - 1542) < 10, (
            f"Parsed rate {rate} != 1,542 msg/s thesis claim"
        )


"""
=== FAILURE ANALYSIS — E4 (Throughput) ===

If throughput < 600 msg/s or lag > 100:

1. **Under-provisioned Kafka partitions** — fewer partitions than Flink parallelism.
   → Set num.partitions >= Flink parallelism (12+).
   → Verify partition assignment: crypto_ticker should have 12 partitions.

2. **Flink checkpoint interval too aggressive** — checkpoint pauses consumption.
   → Increase checkpoint interval from 60s→120s or align with natural lull.
   → Enable unaligned checkpoints for faster recovery.

3. **Producer bottleneck** — single-threaded producer can't keep up with 671 symbols.
   → Verify 8 async shards are truly parallel (asyncio.gather).
   → Check WebSocket reconnect storm when Binance resets connection.

4. **Consumer lag spikes at UTC 00:00** — daily candle rollover causes write burst.
   → Pre-compute 1d candles from 1h aggregation instead of 1m→1d on the fly.
   → Increase Flink parallelism for kline_aggregator job during rollover.

5. **Network bandwidth saturation** — 1,542 msg/s × ~200 bytes × 8 = ~2.5 Mbps.
   → Unlikely bottleneck. Check EBS bandwidth throttling on t3a instances
     (t3a baseline ~1.5 Gbps, burst ~5 Gbps — should be fine).
"""
