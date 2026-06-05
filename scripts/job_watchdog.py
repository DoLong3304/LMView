#!/usr/bin/env python3
import json
import os
import subprocess
import time
from urllib.request import urlopen


FLINK_HEALTH_URL = os.environ.get("FLINK_HEALTH_URL", "http://flink-jobmanager:8081")
SPARK_HEALTH_URL = os.environ.get("SPARK_HEALTH_URL", "http://spark-master:8080")
CHECK_INTERVAL_SEC = int(os.environ.get("JOB_WATCHDOG_INTERVAL_SEC", "300"))


def _json(url: str):
    with urlopen(url, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def flink_healthy() -> bool:
    try:
        jobs = _json(f"{FLINK_HEALTH_URL}/jobs/overview")
        running = [j for j in jobs.get("jobs", []) if j.get("state") in {"RUNNING", "CREATED", "RESTARTING"}]
        return bool(running)
    except Exception:
        return False


def spark_healthy() -> bool:
    try:
        _json(f"{SPARK_HEALTH_URL}/json/")
        return True
    except Exception:
        return False


def submit_jobs() -> None:
    subprocess.run(["bash", "/app/scripts/auto_submit_jobs.sh"], check=False)


def main() -> None:
    while True:
        if not flink_healthy() or not spark_healthy():
            submit_jobs()
        time.sleep(CHECK_INTERVAL_SEC)


if __name__ == "__main__":
    main()
