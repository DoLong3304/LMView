#!/usr/bin/env python3
"""Test specific PromQL expressions."""
import json
import urllib.request
import urllib.parse

QUERIES = [
    "redis_up or 0",
    "up{job='trino'} or 0",
    "up{job='minio'} or 0",
    "redis_up",
    "up{job='trino'}",
    "up{job='minio'}",
    "redis_up or vector(0)",
    "up{job='trino'} or vector(0)",
    "up{job='minio'} or vector(0)",
    "label_replace(redis_up, 'instance', '$1', 'instance', '(.+)') or vector(0)",
]

for q in QUERIES:
    url = f"http://localhost:9090/prometheus/api/v1/query?{urllib.parse.urlencode({'query': q})}"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            d = json.load(r)
            res = d.get("data", {}).get("result", [])
            if res:
                v = res[0].get("value", ["?", "?"])[1]
                print(f"  OK ({len(res)} series, val={v[:20]}): {q}")
            else:
                print(f"  NODATA: {q}")
    except Exception as e:
        print(f"  ERR ({e.__class__.__name__}): {q}")
