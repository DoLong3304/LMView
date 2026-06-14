#!/usr/bin/env python3
"""
Prune dashboards: remove panels whose queries have no data.

Strategy:
- Verify each panel's target expression against Prometheus
- If ALL targets in a panel return NODATA, remove the panel
- If SOME targets return data, keep the panel but remove the bad targets
- Also remove empty rows (collapsible sections) after pruning
- Optionally remove empty/empty-named panels
"""
import json
import os
import sys
import urllib.parse
import urllib.request

PROM_URL = "http://localhost:9090/prometheus/api/v1/query"
DASH_DIR = "config/grafana/dashboards"


def query_prom(expr: str) -> bool:
    try:
        url = f"{PROM_URL}?{urllib.parse.urlencode({'query': expr})}"
        with urllib.request.urlopen(url, timeout=10) as r:
            d = json.load(r)
        return bool(d.get("data", {}).get("result", []))
    except Exception:
        return False


def prune_dashboard(path: str, dry_run: bool = True) -> tuple[int, int]:
    """Returns (panels_kept, panels_removed)."""
    with open(path) as f:
        d = json.load(f)
    orig_panels = d.get("panels", [])
    kept = []
    removed = 0
    targets_removed = 0

    for p in orig_panels:
        ptype = p.get("type", "")
        targets = p.get("targets", [])

        if ptype == "row":
            kept.append(p)
            continue

        if not targets:
            # Panel without targets (e.g., text/markdown) - keep
            kept.append(p)
            continue

        good_targets = []
        bad_targets = 0
        for t in targets:
            expr = t.get("expr", "")
            if not expr:
                continue
            if query_prom(expr):
                good_targets.append(t)
            else:
                bad_targets += 1

        if good_targets:
            p["targets"] = good_targets
            kept.append(p)
            if bad_targets:
                targets_removed += bad_targets
        else:
            removed += 1

    # Optionally remove empty rows
    final = []
    for i, p in enumerate(kept):
        if p.get("type") == "row":
            # Check if next panel is another row or end
            nxt = kept[i + 1] if i + 1 < len(kept) else None
            if nxt is None or nxt.get("type") == "row":
                # Empty row, skip
                continue
        final.append(p)

    if not dry_run:
        d["panels"] = final
        with open(path, "w") as f:
            json.dump(d, f, indent=2)

    return len(final), removed, targets_removed


def main():
    dry_run = "--apply" not in sys.argv
    if dry_run:
        print("=== DRY RUN (use --apply to write) ===\n")
    else:
        print("=== APPLYING ===\n")

    total_kept = 0
    total_removed = 0
    for root, _, files in os.walk(DASH_DIR):
        for f in files:
            if not f.endswith(".json"):
                continue
            path = os.path.join(root, f)
            with open(path) as fp:
                d = json.load(fp)
            if "panels" not in d:
                continue
            npanels = len(d.get("panels", []))
            kept, removed, tremoved = prune_dashboard(path, dry_run=dry_run)
            total_kept += kept
            total_removed += removed
            if removed > 0 or tremoved > 0:
                print(f"  {path}")
                print(f"    panels: {npanels} -> {kept} (removed {removed})")
                if tremoved:
                    print(f"    targets removed: {tremoved}")

    print(f"\n=== Total: kept {total_kept} panels, removed {total_removed} panels ===")


if __name__ == "__main__":
    main()
