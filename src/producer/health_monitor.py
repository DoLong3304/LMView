import logging
import threading
import time
from collections.abc import Callable
from typing import Optional

import requests

from common.config import (
    ENABLE_DIRECT_REDIS,
    FAILOVER_THRESHOLD_SEC,
    FLINK_JM_URL,
    HEALTH_CHECK_INTERVAL_SEC,
    KAFKA_BOOTSTRAP,
    RECOVERY_THRESHOLD_SEC,
)

log = logging.getLogger(__name__)


class HealthMonitor:
    """Monitors producer worker heartbeats and restarts dead threads."""

    def __init__(self, timeout_sec: float = 45.0, check_interval_sec: float = 15.0):
        self.timeout_sec = timeout_sec
        self.check_interval_sec = check_interval_sec
        self._heartbeats: dict[str, float] = {}
        self._starters: dict[str, Callable[[], threading.Thread]] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._lock = threading.Lock()

        # Auto-failover state
        self._direct_redis_active = ENABLE_DIRECT_REDIS
        self._kafka_healthy = True
        self._flink_healthy = True
        self._failure_start_time: Optional[float] = None
        self._recovery_start_time: Optional[float] = None
        self._health_check_interval = HEALTH_CHECK_INTERVAL_SEC

    def register(self, name: str, starter: Callable[[], threading.Thread]) -> None:
        with self._lock:
            self._starters[name] = starter

    def attach_thread(self, name: str, thread: threading.Thread) -> None:
        with self._lock:
            self._threads[name] = thread
            self._heartbeats[name] = time.monotonic()

    def heartbeat(self, name: str) -> None:
        with self._lock:
            self._heartbeats[name] = time.monotonic()

    def start_daemon(self) -> threading.Thread:
        t = threading.Thread(target=self._loop, name="producer-health-monitor", daemon=True)
        t.start()
        return t

    def _loop(self) -> None:
        while True:
            time.sleep(self.check_interval_sec)
            now = time.monotonic()
            to_restart: list[str] = []
            with self._lock:
                for name, starter in self._starters.items():
                    thread = self._threads.get(name)
                    last = self._heartbeats.get(name, 0.0)
                    thread_dead = thread is None or not thread.is_alive()
                    heartbeat_stale = now - last > self.timeout_sec
                    if thread_dead or heartbeat_stale:
                        to_restart.append(name)

            for name in to_restart:
                self._restart(name)

            # Auto-failover check
            self._check_health_and_toggle_redis()

    def _check_health_and_toggle_redis(self) -> None:
        """Check Kafka and Flink health, auto-toggle direct Redis bypass."""
        kafka_ok = self._check_kafka()
        flink_ok = self._check_flink()

        now = time.time()

        with self._lock:
            both_down = not kafka_ok and not flink_ok

            if both_down:
                if self._failure_start_time is None:
                    self._failure_start_time = now
                self._recovery_start_time = None

                elapsed = now - self._failure_start_time
                if elapsed >= FAILOVER_THRESHOLD_SEC and not self._direct_redis_active:
                    log.warning(
                        "[HEALTH] Kafka and Flink down for %.0fs, enabling direct Redis bypass",
                        elapsed,
                    )
                    self._direct_redis_active = True
                    self._notify_redis_toggle(True)

            else:
                if self._failure_start_time is not None:
                    if self._recovery_start_time is None:
                        self._recovery_start_time = now

                    elapsed = now - self._recovery_start_time
                    if elapsed >= RECOVERY_THRESHOLD_SEC and self._direct_redis_active:
                        log.info(
                            "[HEALTH] Kafka/Flink recovered for %.0fs, disabling direct Redis bypass",
                            elapsed,
                        )
                        self._direct_redis_active = False
                        self._failure_start_time = None
                        self._recovery_start_time = None
                        self._notify_redis_toggle(False)
                else:
                    self._recovery_start_time = None

            self._kafka_healthy = kafka_ok
            self._flink_healthy = flink_ok

    def _check_kafka(self) -> bool:
        """Check if Kafka bootstrap is reachable."""
        try:
            brokers = KAFKA_BOOTSTRAP.split(",")
            if not brokers:
                return False
            host_port = brokers[0].strip()
            host = host_port.split(":")[0]
            port = int(host_port.split(":")[1]) if ":" in host_port else 9092

            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception as e:
            log.debug("[HEALTH] Kafka check failed: %s", e)
            return False

    def _check_flink(self) -> bool:
        """Check if Flink JobManager is reachable and has running jobs."""
        try:
            resp = requests.get(f"{FLINK_JM_URL}/jobs", timeout=5)
            if resp.status_code == 200:
                jobs = resp.json()
                return jobs.get("jobs", []) or len(jobs.get("jobs", [])) > 0
            return False
        except Exception as e:
            log.debug("[HEALTH] Flink check failed: %s", e)
            return False

    def _notify_redis_toggle(self, enabled: bool) -> None:
        """Notify direct writer of state change."""
        try:
            from exchanges.binance.redis_writer import set_direct_redis_active
            set_direct_redis_active(enabled)
        except Exception as e:
            log.error("[HEALTH] Failed to notify Redis writer: %s", e)

    def is_direct_redis_active(self) -> bool:
        with self._lock:
            return self._direct_redis_active

    def get_health_status(self) -> dict:
        with self._lock:
            return {
                "kafka_healthy": self._kafka_healthy,
                "flink_healthy": self._flink_healthy,
                "direct_redis_active": self._direct_redis_active,
                "failure_duration_sec": (
                    time.time() - self._failure_start_time
                    if self._failure_start_time else 0
                ),
            }

    def _restart(self, name: str) -> None:
        with self._lock:
            starter = self._starters.get(name)
            if starter is None:
                return
        log.warning("[HEALTH] Restarting worker %s", name)
        thread = starter()
        with self._lock:
            self._threads[name] = thread
            self._heartbeats[name] = time.monotonic()
