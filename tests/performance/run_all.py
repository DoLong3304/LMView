#!/usr/bin/env python3
"""
Orchestration runner: execute all Chapter 4 evaluation tests.

Usage:
    python -m pytest tests/performance/ -v --tb=short
    python tests/performance/run_all.py                    # summary mode

Generates: tests/performance/report.md with pass/fail per E1-E6.
"""

import os
import sys
import json
import subprocess
from datetime import datetime


REPORT_PATH = os.path.join(os.path.dirname(__file__), "report.md")
THESIS_TARGETS = {
    "E1": {"p50": 212, "p95": 387, "p99": 468, "target_p50": 200, "target_p99": 500},
    "E2a": {"p50": 12.3, "p95": 28.7, "p99": 45.2, "target_p50": 50, "target_p99": 200},
    "E2b": {"p50": 18.5, "p95": 52.3, "p99": 78.1, "target_p50": 50, "target_p99": 200},
    "E2c": {"p50": 45.6, "p95": 112.4, "p99": 168.9, "target_p50": 50, "target_p99": 200},
    "E2d": {"p50": 8.7, "p95": 32.1, "p99": 58.3, "target_p50": 50, "target_p99": 200},
    "E2f": {"p50": 215.3, "p95": 423.7, "p99": 489.2, "target_p50": 500, "target_p99": 2000},
    "E2g": {"p50": 6.2, "p95": 18.9, "p99": 32.4, "target_p50": 50, "target_p99": 200},
    "E3": {"p50": 50.2, "p95": 52.8, "p99": 58.1, "target_p95": 100},
    "E4": {"throughput": 1542, "lag_max": 87, "target_throughput": 600, "target_lag": 100},
    "E5": {"avg": 11.2, "min": 8.7, "max": 15.3, "target": 30},
    "E6": {"uptime": 99.95, "checks": 2016, "failures": 1, "target": 99.9},
}


def run_pytest() -> dict:
    """Run pytest on performance tests, return parsed results."""
    cmd = [
        sys.executable, "-m", "pytest",
        os.path.dirname(__file__),
        "-v", "--tb=short",
        "--json-report",  # requires pytest-json-report
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120
        )
    except subprocess.TimeoutExpired:
        return {"error": "timeout", "stdout": "", "stderr": "Tests timed out (120s)"}

    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def generate_report(pytest_results: dict) -> str:
    """Generate markdown report comparing test results vs thesis claims."""
    lines = []
    lines.append("# LMView Chapter 4 — Evaluation Test Report\n")
    lines.append(f"Generated: {datetime.now().isoformat()}\n")
    lines.append("## Summary\n")
    lines.append("| Criteria | Thesis Value | Target | Status |\n")
    lines.append("|----------|-------------|--------|--------|\n")

    for crit, values in THESIS_TARGETS.items():
        target_str = values.get("target", values.get("target_p50", "N/A"))
        thesis_val = values.get("p50", values.get("throughput", values.get("avg", values.get("uptime", "N/A"))))
        lines.append(f"| {crit} | {thesis_val} | {target_str} | Pending |\n")

    if pytest_results.get("error"):
        lines.append(f"\n## Execution Error\n{pytest_results['error']}\n")

    lines.append(f"\n## Raw Test Output\n```\n{pytest_results.get('stdout', '')[-2000:]}\n```\n")
    if pytest_results.get("stderr"):
        lines.append(f"## Stderr\n```\n{pytest_results['stderr'][-1000:]}\n```\n")

    lines.append("\n## Failure Analysis\n")
    lines.append("See individual test files for detailed root cause analysis:\n")
    for crit in THESIS_TARGETS:
        lines.append(f"- `test_e{crit.lower().replace('2', '2_').split('_')[0]}_*.py`\n")

    return "".join(lines)


def print_summary(pytest_results: dict):
    """Print human-readable summary to stdout."""
    rc = pytest_results.get("returncode", -1)
    print(f"\n{'='*60}")
    print(f"  CHAPTER 4 EVALUATION TEST SUITE")
    print(f"  Exit code: {rc} {'✅ All passed' if rc == 0 else '❌ Some failed'}")
    print(f"{'='*60}\n")

    for test_id, targets in THESIS_TARGETS.items():
        print(f"  {test_id}: thesis={targets.get('p50', targets.get('throughput', '?'))}")


if __name__ == "__main__":
    print("Running Chapter 4 performance test suite...")
    results = run_pytest()
    print_summary(results)

    report = generate_report(results)
    with open(REPORT_PATH, "w") as f:
        f.write(report)
    print(f"\nReport saved to: {REPORT_PATH}")
    sys.exit(results.get("returncode", 1))
