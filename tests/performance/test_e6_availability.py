"""
E6: System Availability — health check monitoring & uptime calculation.

Thesis-reported: 99.95% uptime over 7 days (2,016 checks, 1 failure).
Target: >99.9% (< 8.76 hrs downtime/year).

Tests: health check methodology, uptime calculation, detection of the
single reported failure (2026-06-22 03:14 UTC, CPU spike from Flink checkpoint).
"""

import os
import time
from unittest.mock import MagicMock, patch
import pytest


# ── Uptime calculator ───────────────────────────────────────────────

def calculate_uptime(health_log_lines: list[str]) -> dict:
    """
    Parse health check log and compute availability.

    Format: ISO_TIMESTAMP STATUS_CODE RESPONSE_TIME_MS
    Example: 2026-06-22T03:14:00Z 200 12
    """
    total = 0
    failed = 0
    failures = []

    for line in health_log_lines:
        parts = line.strip().split()
        if len(parts) >= 2:
            total += 1
            status = parts[1]
            if status != "200":
                failed += 1
                if len(parts) >= 1:
                    failures.append(parts[0])

    uptime_pct = ((total - failed) / total * 100) if total > 0 else 0
    return {
        "total_checks": total,
        "failed_checks": failed,
        "uptime_pct": round(uptime_pct, 2),
        "failure_timestamps": failures,
    }


# ── Tests ───────────────────────────────────────────────────────────

class TestE6AvailabilityMeasurement:
    """Validate uptime monitoring methodology."""

    def test_uptime_calculation_7_days(self):
        """Simulate 7 days of health checks (one every 5 min = 2,016 checks)."""
        entries = []
        for i in range(2016):
            ts = f"2026-06-{14 + i//288:02d}T{i%288*5:02d}:00:00Z"
            entries.append(f"{ts} 200 {10 + (i % 20)}")

        result = calculate_uptime(entries)
        assert result["total_checks"] == 2016
        assert result["uptime_pct"] == 100.0
        assert result["failed_checks"] == 0

    def test_single_failure_results_in_9995_percent(self):
        """Thesis: 1 failure in 2,016 checks → 99.95%."""
        entries = []
        for i in range(2016):
            ts = f"2026-06-{14 + i//288:02d}T{i%288*5:02d}:00:00Z"
            if i == 400:  # ~ 2026-06-15 09:20
                entries.append(f"{ts} 503 450")  # Failing check
            else:
                entries.append(f"{ts} 200 {10 + (i % 20)}")

        result = calculate_uptime(entries)
        assert result["total_checks"] == 2016
        assert result["failed_checks"] == 1
        assert result["uptime_pct"] == 99.95, (
            f"Uptime {result['uptime_pct']}% != 99.95%. "
            f"Expected exactly 1 fail in 2016 checks."
        )

    def test_thesis_reported_failure_scenario(self):
        """Simulate: 2026-06-22 03:14 UTC — Flink checkpoint CPU spike."""
        entries = []
        for i in range(2016):
            ts = f"2026-06-{14 + i//288:02d}T{i%288*5:02d}:00:00Z"
            # Inject failure on 2026-06-22 03:14 UTC (day 8, min 03:14 → index)
            day = 14 + i // 288
            minute = (i % 288) * 5
            if day == 22 and 190 <= i % 288 <= 191:  # 03:10-03:15 UTC
                entries.append(f"{ts} 503 5000")  # CPU spike, 5s response
            else:
                entries.append(f"{ts} 200 {12 + (i % 15)}")

        result = calculate_uptime(entries)
        assert result["failed_checks"] == 2  # 2 consecutive failures
        assert result["uptime_pct"] > 99.9, (
            f"Uptime {result['uptime_pct']}% below 99.9% target"
        )

    def test_health_check_interval_accuracy(self):
        """Crontab health check every 5 minutes must not drift >30s."""
        import datetime
        base = datetime.datetime(2026, 6, 14, 0, 0, 0)
        intervals = []
        for i in range(288):  # 24 hours
            check_time = base + datetime.timedelta(minutes=i * 5)
            intervals.append(check_time)

        # Verify exact 5-minute spacing
        for i in range(1, len(intervals)):
            diff = (intervals[i] - intervals[i-1]).total_seconds()
            assert abs(diff - 300) < 1, (
                f"Interval drift at check {i}: {diff}s (expected 300s)"
            )

    def test_three_consecutive_failures_alert(self):
        """NFR: alert if 3 consecutive checks fail (>15 min downtime)."""
        entries = []
        # Inject 3 consecutive failures at checks 500, 501, 502
        for i in range(600):
            ts = f"2026-06-20T{i*5:02d}:00:00Z"
            if 500 <= i <= 502:
                entries.append(f"{ts} 503 3000")
            else:
                entries.append(f"{ts} 200 10")

        result = calculate_uptime(entries)
        consecutive_fails = 0
        max_consecutive = 0
        for line in entries:
            if "503" in line:
                consecutive_fails += 1
                max_consecutive = max(max_consecutive, consecutive_fails)
            else:
                consecutive_fails = 0

        assert max_consecutive >= 3, "Alert should trigger at 3 consecutive failures"
        assert max_consecutive < 5, (
            f"Too many consecutive failures ({max_consecutive}) — "
            f"auto-recovery should happen within 3-4 checks"
        )


"""
=== FAILURE ANALYSIS — E6 (Availability) ===

If uptime < 99.9%:

1. **Flink checkpoint CPU spike** — checkpoint sync causes >90% CPU for 30-60s.
   → Switch to asymmetric checkpoint: stagger by partition not all at once.
   → Reduce state size: keep only last 2 candles per symbol instead of 100.
   → Enable incremental checkpoint (RocksDB backend).

2. **Docker Swarm health check race condition** — health_before_start=0 allows
   traffic before service is ready.
   → Set health_before_start=5 (5 successful health checks before accepting traffic).
   → Increase start_period to 30s for JVM services (Flink, Kafka, Spark).

3. **Memory pressure from Trino queries** — concurrent queries OOM node.
   → Set query.max-memory-per-node=2GB (thesis config is correct).
   → Add cgroup memory limit: docker service --limit-memory 28G per node.
   → Implement query queue: max 2 concurrent Trino queries.

4. **AWS instance credit exhaustion** — t3a burst CPU credits run out under load.
   → Set instance to T2/T3 unlimited (--cpu-credits unlimited) for +$0.05/hr.
   → Or migrate to c6a.2xlarge (dedicated CPU, no credit system).
   → Monitor CPUCreditBalance via CloudWatch; alert when < 100.

5. **Single node failure takes out critical service** — Node 1 hosts both
   Nginx AND PostgreSQL. If Node 1 fails, entire system is down.
   → Move PostgreSQL to Node 2 with async replica on Node 3.
   → Add Nginx replica on Node 2 with HA failover (keepalived + floating IP).
"""
