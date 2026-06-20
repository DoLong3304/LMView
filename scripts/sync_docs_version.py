#!/usr/bin/env python3
"""sync_docs_version.py — Atomically update version across all .md files.

Usage:
    python scripts/sync_docs_version.py [--dry-run] [--version X.Y.Z]

If --version is omitted, reads from VERSION file at repo root.
If VERSION file doesn't exist, parses latest from docs/CHANGELOG.md.

Strategy: Define regex patterns that capture the version string as group(1).
For each match, replace only the captured portion while preserving surrounding text.
"""

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# ── Patterns ────────────────────────────────────────────────────────────
# Each pattern MUST have exactly one capture group: the version number.
# The replacer replaces only that group, preserving prefix/suffix.
PATTERNS: list[str] = [
    # Release: **X.Y.Z**
    r'\*\*(\d+\.\d+\.\d+)\*\*',
    # Version: **vX.Y.Z**
    r'Version\s*:\s*\*\*v?(\d+\.\d+\.\d+)\*\*',
    # Current release: `X.Y.Z`
    r'Current release: `(\d+\.\d+\.\d+)`',
    # YAML front matter version: X.Y.Z
    r'^version:\s*(\d+\.\d+\.\d+)',
    # | Version: X.Y.Z (with optional bold markers)
    r'\|\s*Version:\s*\*?(\d+\.\d+\.\d+)\*?',
    # Status line ... | Version: X.Y.Z or standalone Version: X.Y.Z
    r'\bVersion:\s*\*?(\d+\.\d+\.\d+)\*?',
    # version="X.Y.Z" in backend/app.py
    r'version="(\d+\.\d+\.\d+)"',
]


def get_current_version() -> str:
    version_file = REPO_ROOT / 'VERSION'
    if version_file.exists():
        return version_file.read_text().strip()
    changelog = REPO_ROOT / 'docs' / 'CHANGELOG.md'
    if changelog.exists():
        for line in changelog.read_text().splitlines():
            m = re.match(r'^## \[(\d+\.\d+\.\d+)\]', line)
            if m:
                return m.group(1)
    print("ERROR: No VERSION file or CHANGELOG.md found.", file=sys.stderr)
    sys.exit(1)


def collect_md_files() -> list[Path]:
    files = []
    for path in REPO_ROOT.rglob('*.md'):
        rel = path.relative_to(REPO_ROOT)
        parts = rel.parts
        if any(p in parts for p in ('trash', 'node_modules', '.git', '.claude',
                                     '__pycache__', '.venv', 'venv')):
            continue
        files.append(path)
    return sorted(files)


def make_replacer(version: str):
    """Return a replacer function for re.sub that replaces group(1) with version."""
    def replacer(m: re.Match) -> str:
        start = m.start(1)
        end = m.end(1)
        return m.string[m.start():start] + version + m.string[end:m.end()]
    return replacer


def sync_version(version: str, dry_run: bool = False) -> int:
    total_changes = 0
    files_to_update: list = []

    for md_path in collect_md_files():
        try:
            original = md_path.read_text(encoding='utf-8')
        except Exception:
            continue

        content = original
        changes = 0

        for pattern in PATTERNS:
            replacer = make_replacer(version)
            new_content, count = re.subn(pattern, replacer, content)
            if count > 0:
                changes += count
                content = new_content

        if changes > 0:
            files_to_update.append((md_path, content, changes))
            total_changes += changes

    if not files_to_update:
        print(f"OK Version {version}: no files needed updating.")
        return 0

    print(f"Version {version}: {len(files_to_update)} file(s), {total_changes} change(s):")
    for path, _, chg in sorted(files_to_update, key=lambda x: str(x[0])):
        print(f"  {chg:3d}  {path.relative_to(REPO_ROOT)}")

    if not dry_run:
        for path, content, _ in files_to_update:
            path.write_text(content, encoding='utf-8')
        print(f"\nWritten {total_changes} change(s) across {len(files_to_update)} file(s).")
    else:
        print("\nDry-run — no files written.")

    return total_changes


def main() -> None:
    p = argparse.ArgumentParser(description='Sync version across all markdown docs.')
    p.add_argument('--version', '-v', default=None,
                   help='Version string (e.g. 0.25.42). Default: read from VERSION or CHANGELOG.')
    p.add_argument('--dry-run', '-n', action='store_true',
                   help='Preview changes without writing.')
    args = p.parse_args()
    version = args.version or get_current_version()
    if not re.match(r'^\d+\.\d+\.\d+$', version):
        print(f"ERROR: Invalid version format '{version}'. Use X.Y.Z.", file=sys.stderr)
        sys.exit(1)
    sync_version(version, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
