#!/usr/bin/env python3
"""watchdog_flink_job.py — Pure-Python Flink pipeline supervisor.

Polls Flink jobmanager every 30s. If no jobs are running but slots are
available, submits processing/pipeline.py via the Flink REST API.

Designed to run as a long-lived container with python3 available.

Env vars:
  FLINK_JM_URL   Flink JobManager URL (default http://localhost:8081)
  REDIS_HOST     Redis hostname (default redis-master)
  PROJECT_DIR    Project root directory (default /mnt/efs/LMView)
  FLINK_IMAGE    Flink Docker image tag (default localhost:5000/cryptoprice/flink:1.18.1)
  INTERVAL_SEC   Poll interval in seconds (default 30)
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import time
import urllib.error
import urllib.request

FLINK_JM_URL = os.environ.get("FLINK_JM_URL", "http://localhost:8081")
REDIS_HOST = os.environ.get("REDIS_HOST", "redis-master")
PROJECT_DIR = os.environ.get("PROJECT_DIR", "/mnt/efs/LMView")
FLINK_IMAGE = os.environ.get("FLINK_IMAGE", "localhost:5000/cryptoprice/flink:1.18.1")
INTERVAL = int(os.environ.get("INTERVAL_SEC", "30"))


def http_get_json(url: str, timeout: int = 5) -> dict | None:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def redis_hlen(key: str) -> int:
    s = socket.socket()
    s.settimeout(3)
    try:
        s.connect((REDIS_HOST, 6379))
        parts = ["*2", f"$4", "HLEN", f"${len(key)}", key]
        cmd = "\r\n".join(parts) + "\r\n"
        s.send(cmd.encode())
        out = s.recv(64).decode(errors="replace").strip()
        if out.startswith(":"):
            return int(out[1:])
    finally:
        s.close()
    return 0


def submit_job() -> bool:
    """Submit Flink pipeline via subprocess (uses flink image's flink CLI)."""
    # Extract host from FLINK_JM_URL for the -m argument
    flink_host = FLINK_JM_URL.replace("http://", "").replace("https://", "")
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{PROJECT_DIR}:{PROJECT_DIR}:ro",
        FLINK_IMAGE,
        "bash", "-c",
        (
            "cd /tmp && "
            f"SRC_DIR={PROJECT_DIR}/src "
            f"bash {PROJECT_DIR}/scripts/build_deps_zip.sh && "
            f"flink run -m {flink_host} -d "
            f"-pyfs {PROJECT_DIR}/src/processing "
            f"--pyFiles {PROJECT_DIR}/deps.zip "
            f"--python {PROJECT_DIR}/src/processing/pipeline.py"
        ),
    ]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if out.returncode == 0 and "Job has been submitted" in out.stdout:
            line = [l for l in out.stdout.strip().splitlines() if "Job has been submitted" in l]
            print(f"[watchdog] ✅ Flink job submitted: {line[-1] if line else out.stdout.strip()}")
            return True
        print(f"[watchdog] ❌ submit failed: rc={out.returncode}")
        print(f"            stdout: {out.stdout[-300:]}")
        print(f"            stderr: {out.stderr[-300:]}")
        return False
    except subprocess.TimeoutExpired:
        print("[watchdog] ⏱️  submit timed out")
        return False
    except FileNotFoundError:
        # docker not on PATH (inside a container without docker CLI)
        print("[watchdog] ⚠️  docker CLI not available — cannot submit")
        return False


def main() -> None:
    print(f"[watchdog] starting (flink={FLINK_JM_URL} redis={REDIS_HOST} interval={INTERVAL}s)")
    while True:
        overview = http_get_json(f"{FLINK_JM_URL}/overview")
        if overview is None:
            print("[watchdog] ⚠️  Flink not reachable")
            time.sleep(INTERVAL)
            continue

        tms = overview.get("taskmanagers", 0)
        slots_avail = overview.get("slots-available", 0)
        jobs = http_get_json(f"{FLINK_JM_URL}/jobs") or {}
        running = sum(1 for j in jobs.get("jobs", []) if j.get("status") == "RUNNING")

        print(f"[watchdog] tms={tms} slots={slots_avail} jobs_running={running}")

        if running == 0 and slots_avail > 0:
            print(f"[watchdog] ⚠️  no jobs running but {slots_avail} slots free — resubmitting")
            submit_job()

        solusdt_fields = redis_hlen("indicator:latest:binance:SOLUSDT")
        if solusdt_fields > 0:
            print(f"[watchdog] ✅ SOLUSDT indicator has {solusdt_fields} fields")

        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
