#!/usr/bin/env python
"""Verify every PromQL/Loki query in every Grafana dashboard via Grafana API.

For each dashboard:
  - Fetch full dashboard JSON via /api/dashboards/uid/{uid}
  - For each panel, for each target, send the expression to the right datasource
  - Report OK (has data) / NODATA / ERR

This is the authoritative check because it goes through Grafana's
datasource proxy (same as what the dashboard renders).
"""
import json
import urllib.request
import urllib.parse
import base64
import sys

GRAFANA = "http://localhost:3001"
AUTH = base64.b64encode(b"admin:admin123").decode()


def http_get_json(url):
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Basic {AUTH}")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def http_post_json(url, payload):
    req = urllib.request.Request(url, data=json.dumps(payload).encode())
    req.add_header("Authorization", f"Basic {AUTH}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def query_via_grafana(ds_uid, expr, ref_id="A", time_from="now-1h", time_to="now"):
    """Send query to Grafana datasource proxy and return result count.

    For templating variables ($var), we don't substitute - Grafana
    resolves them. We test with `__all` as default to test 'any' behaviour.
    """
    # Note: variables must be replaced before sending
    expr_sub = expr
    if "$" in expr:
        # Replace $var with .+ (regex match-all) for PromQL,
        # or with .+ (regex match-all) for Loki
        import re
        expr_sub = re.sub(r"\$\w+", ".+", expr)

    payload = {
        "queries": [
            {
                "refId": ref_id,
                "datasource": {"type": _ds_type(ds_uid), "uid": ds_uid},
                "expr": expr_sub,
                "intervalMs": 60000,
                "maxDataPoints": 100,
            }
        ],
        "from": time_from,
        "to": time_to,
    }
    try:
        d = http_post_json(f"{GRAFANA}/api/ds/query", payload)
        results = d.get("results", {})
        r = results.get(ref_id, {})
        # Prom response: frames; Loki response: streams
        frames = r.get("frames", [])
        if frames:
            # Has at least one frame with data
            for f in frames:
                data = f.get("data", {}).get("values", [])
                # For Loki logs, values[0] is label dicts, values[1] is timestamps
                # For Prom, values[0] is timestamps, values[1] is values
                # Check values[1] (or values[0] if short) for actual data
                for col in data:
                    if isinstance(col, list) and len(col) > 0:
                        return "OK", len(col)
                return "NODATA", 0
            return "NODATA", 0
        # Loki streams format (older)
        streams = r.get("data", {}).get("result", [])
        if streams:
            return "OK", sum(len(s.get("values", [])) for s in streams)
        return "NODATA", 0
    except Exception as e:
        # Retry once on timeout
        try:
            d = http_post_json(f"{GRAFANA}/api/ds/query", payload)
            results = d.get("results", {})
            r = results.get(ref_id, {})
            frames = r.get("frames", [])
            if frames:
                for f in frames:
                    data = f.get("data", {}).get("values", [])
                    for col in data:
                        if isinstance(col, list) and len(col) > 0:
                            return "OK", len(col)
                    return "NODATA", 0
                return "NODATA", 0
            streams = r.get("data", {}).get("result", [])
            if streams:
                return "OK", sum(len(s.get("values", [])) for s in streams)
            return "NODATA", 0
        except Exception as e2:
            return f"ERR: {e2}", 0


def _ds_type(uid):
    return {"prometheus": "prometheus", "loki": "loki", "influxdb": "influxdb"}.get(uid, "unknown")


def _resolve_ds_type(target):
    """Resolve datasource type from target, handling both uid and type formats."""
    ds = target.get("datasource", {})
    if isinstance(ds, dict):
        uid = ds.get("uid", "")
        type_ = ds.get("type", "")
        if uid in ("prometheus", "loki", "influxdb"):
            return uid
        # Some targets use type only (no uid)
        if type_ in ("prometheus", "loki"):
            return type_
    return None


def main():
    # Get all dashboards
    dlist = http_get_json(f"{GRAFANA}/api/search?type=dash-db")
    bad_total = 0
    tested_total = 0
    skipped_total = 0
    summary = []
    for d in dlist:
        if d.get("folderTitle") in ("General", None):
            continue
        uid = d["uid"]
        try:
            full = http_get_json(f"{GRAFANA}/api/dashboards/uid/{uid}")
        except Exception as e:
            print(f"  ERR loading {uid}: {e}")
            continue
        dashboard = full.get("dashboard", {})
        title = dashboard.get("title", "?")
        folder = d.get("folderTitle", "?")
        time_range = dashboard.get("time", {})
        time_from = time_range.get("from", "now-1h")
        time_to = time_range.get("to", "now")
        bad = 0
        ok = 0
        skipped = 0
        for p in dashboard.get("panels", []):
            p_title = p.get("title", "?")
            for t in p.get("targets", []):
                expr = t.get("expr", "")
                if not expr:
                    continue
                ds = t.get("datasource", {}).get("uid") or t.get("datasource", {}).get("type", "")
                if not ds or ds == "grafana" or "influxdb" in ds:
                    skipped += 1
                    continue
                if ds not in ("prometheus", "loki"):
                    skipped += 1
                    continue
                status, count = query_via_grafana(ds, expr, t.get("refId", "A"), time_from, time_to)
                tested_total += 1
                if status == "OK":
                    ok += 1
                else:
                    bad += 1
                    bad_total += 1
                    print(f"  [BAD] {folder}/{title} | {p_title} | {status} | {expr[:80]}")
        summary.append((folder, title, len(dashboard.get("panels", [])), tested_total, ok, bad, skipped))

    print(f"\n=== Summary ===")
    print(f"  Dashboards: {len(summary)}")
    print(f"  Queries tested: {tested_total}")
    print(f"  BAD: {bad_total}")
    print(f"\n  Per dashboard:")
    for folder, title, panels, t, ok, bad, sk in summary:
        print(f"    {folder:18s} | {title:50s} | panels={panels:3d} tested={t:3d} OK={ok:3d} BAD={bad:3d} skip={sk:3d}")


if __name__ == "__main__":
    main()
