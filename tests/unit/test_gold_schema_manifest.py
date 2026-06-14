"""
Tests for P1 fix: Gold table schema manifest.

The manifest at ``src/lakehouse/gold_schema_manifest.py`` is the
canonical source of truth for which Gold tables exist and which are
deprecated. The API code in ``backend/api/market_overview.py`` and
the Dagster schedule in ``orchestration/assets.py`` must be aligned
with it.

Run with::

    PYTHONPATH=. python -m pytest tests/unit/test_gold_schema_manifest.py -v
"""

from __future__ import annotations

import ast
import os
import re
import sys
from pathlib import Path

# Add src to path
REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "src"))

import pytest


# ── Schema manifest tests ──────────────────────────────────────────────────


class TestSchemaManifestExists:
    """Manifest file must exist and be importable."""

    def test_manifest_file_exists(self):
        path = REPO / "src" / "lakehouse" / "gold_schema_manifest.py"
        assert path.exists(), "gold_schema_manifest.py must exist"
        assert path.stat().st_size > 1000, "Manifest too small"

    def test_manifest_imports(self):
        from lakehouse.gold_schema_manifest import (
            CANONICAL_GOLD_TABLES,
            DEPRECATED_SPARK_TABLES,
            list_canonical_tables,
            get_table_schema,
            is_deprecated_spark_table,
        )
        assert isinstance(CANONICAL_GOLD_TABLES, dict)
        assert isinstance(DEPRECATED_SPARK_TABLES, dict)
        assert callable(list_canonical_tables)
        assert callable(get_table_schema)
        assert callable(is_deprecated_spark_table)


class TestCanonicalSchemaContents:
    """Canonical tables must have all the columns the API needs."""

    @pytest.mark.parametrize("table_name", [
        "gold_movers_ranking",
        "gold_market_dominance",
        "gold_volatility_ranking",
        "gold_momentum_indicators",
        "gold_sector_performance",
        "gold_news_sentiment_daily",
    ])
    def test_canonical_table_in_manifest(self, table_name):
        from lakehouse.gold_schema_manifest import CANONICAL_GOLD_TABLES
        assert table_name in CANONICAL_GOLD_TABLES, (
            f"Canonical table {table_name} missing from manifest"
        )

    @pytest.mark.parametrize("table_name,expected_cols", [
        ("gold_movers_ranking", ["symbol", "exchange", "price", "change_24h",
                                  "volume_24h", "rank_gainers", "rank_losers",
                                  "computed_at"]),
        ("gold_market_dominance", ["symbol", "exchange", "volume_24h",
                                    "volume_pct", "computed_at",
                                    "active_symbols", "total_volume_24h",
                                    "btc_dominance_pct", "eth_dominance_pct"]),
        ("gold_volatility_ranking", ["symbol", "exchange", "price_range_pct",
                                      "atr_estimate", "rank", "computed_at"]),
        ("gold_momentum_indicators", ["symbol", "exchange", "rsi_signal",
                                        "trend_direction", "macd_signal",
                                        "score", "computed_at"]),
        ("gold_sector_performance", ["sector", "avg_change_pct",
                                      "total_volume", "symbol_count",
                                      "computed_at"]),
        ("gold_news_sentiment_daily", ["date", "symbol", "avg_sentiment",
                                        "article_count", "bullish_count",
                                        "bearish_count"]),
    ])
    def test_canonical_table_has_required_columns(self, table_name, expected_cols):
        from lakehouse.gold_schema_manifest import CANONICAL_GOLD_TABLES
        schema = CANONICAL_GOLD_TABLES[table_name]
        for col in expected_cols:
            assert col in schema, (
                f"Column {col} missing from canonical schema for {table_name}"
            )

    def test_computed_at_present_in_every_table(self):
        """Every per-row table has computed_at for the freshness filter,
        OR a documented exception:
          - whale_alerts: trade_time (also Redis sorted-set score)
          - gold_news_sentiment_daily: date (news is daily-grained)
          - liquidity_heatmap: time_bucket (the InfluxDB time is the
            freshness marker; computed_at is a separate audit field)
        """
        from lakehouse.gold_schema_manifest import CANONICAL_GOLD_TABLES
        for table, schema in CANONICAL_GOLD_TABLES.items():
            if table == "gold_news_sentiment_daily":
                assert "date" in schema, f"{table} needs 'date' column"
            elif table == "whale_alerts":
                assert "trade_time" in schema, (
                    f"{table} needs 'trade_time' as freshness marker"
                )
            elif table == "liquidity_heatmap":
                # InfluxDB time IS the freshness marker; the schema
                # also has implicit `time` from the measurement.
                assert "time_bucket" in schema, (
                    f"{table} needs 'time_bucket' as freshness marker"
                )
            else:
                assert "computed_at" in schema, (
                    f"{table} needs 'computed_at' for freshness filter"
                )

    def test_canonical_table_count(self):
        """Nine canonical tables (P0/P1 + Task 2 + Task 4 + Task 5).
        Adding a new one should require updating this test and the
        API code together."""
        from lakehouse.gold_schema_manifest import CANONICAL_GOLD_TABLES
        assert len(CANONICAL_GOLD_TABLES) == 9


class TestDeprecatedSparkTables:
    """Spark-only tables that are no longer used."""

    def test_all_spark_tables_listed(self):
        from lakehouse.gold_schema_manifest import DEPRECATED_SPARK_TABLES
        # These are the Spark-based tables that were running before P1.
        expected = {
            "market_dominance",
            "volatility_ranking",
            "movers_ranking",
            "gold_market_overview",
            "gold_sector_performance",
            "gold_symbol_stats_daily",
        }
        assert set(DEPRECATED_SPARK_TABLES.keys()) == expected

    def test_deprecation_rationale_present(self):
        from lakehouse.gold_schema_manifest import DEPRECATED_SPARK_TABLES
        for table, reason in DEPRECATED_SPARK_TABLES.items():
            assert "No API consumer" in reason or "Replaced by" in reason, (
                f"{table} deprecation must explain why: {reason!r}"
            )

    def test_no_overlap_with_canonical(self):
        """A table is either canonical or deprecated, never both."""
        from lakehouse.gold_schema_manifest import (
            CANONICAL_GOLD_TABLES,
            DEPRECATED_SPARK_TABLES,
        )
        canonical = set(CANONICAL_GOLD_TABLES.keys())
        deprecated = set(DEPRECATED_SPARK_TABLES.keys())
        # ``gold_sector_performance`` is BOTH canonical (Trino) and
        # deprecated (Spark version) — that's the whole point of
        # the rename/unification. We assert they DON'T fully overlap
        # so we don't accidentally flag this in the future as a bug.
        # The canonical wins.
        assert "gold_sector_performance" in canonical
        assert "gold_sector_performance" in deprecated
        # …but for any other table, it must be in exactly one set.
        other_overlap = (canonical & deprecated) - {"gold_sector_performance"}
        assert not other_overlap, (
            f"Other tables cannot be in both: {other_overlap}"
        )


class TestHelperFunctions:
    """list_canonical_tables / get_table_schema / is_deprecated_spark_table."""

    def test_list_canonical_tables_returns_list(self):
        from lakehouse.gold_schema_manifest import list_canonical_tables
        tables = list_canonical_tables()
        assert isinstance(tables, list)
        assert "gold_movers_ranking" in tables

    def test_get_table_schema_known(self):
        from lakehouse.gold_schema_manifest import get_table_schema
        schema = get_table_schema("gold_movers_ranking")
        assert schema is not None
        assert "symbol" in schema

    def test_get_table_schema_unknown(self):
        from lakehouse.gold_schema_manifest import get_table_schema
        assert get_table_schema("unknown_table") is None

    def test_is_deprecated_spark_table_true(self):
        from lakehouse.gold_schema_manifest import is_deprecated_spark_table
        assert is_deprecated_spark_table("market_dominance") is True
        assert is_deprecated_spark_table("gold_symbol_stats_daily") is True

    def test_is_deprecated_spark_table_false(self):
        from lakehouse.gold_schema_manifest import is_deprecated_spark_table
        assert is_deprecated_spark_table("gold_movers_ranking") is False
        assert is_deprecated_spark_table("nonexistent") is False


class TestFreshnessConstant:
    """GOLD_FRESHNESS_MINUTES must match API default for compatibility."""

    def test_freshness_value(self):
        from lakehouse.gold_schema_manifest import GOLD_FRESHNESS_MINUTES
        assert GOLD_FRESHNESS_MINUTES == 30

    def test_api_uses_manifest_constant(self):
        """The API should import GOLD_FRESHNESS_MINUTES from the manifest
        rather than redefine its own. This test guards against drift.
        """
        api_path = REPO / "backend" / "api" / "market_overview.py"
        api_src = api_path.read_text(encoding="utf-8")
        assert "gold_schema_manifest" in api_src, (
            "backend/api/market_overview.py must reference the manifest"
        )
        # If manifest import fails, there should be a fallback
        assert "GOLD_FRESHNESS_MINUTES" in api_src


# ── Dagster asset alignment tests ──────────────────────────────────────────


class TestDagsterAssetsDeferDeprecated:
    """The Spark-based gold_advanced assets must be disabled in Dagster."""

    @pytest.fixture
    def assets_src(self):
        path = REPO / "orchestration" / "assets.py"
        return path.read_text(encoding="utf-8")

    def test_assets_module_parses(self, assets_src):
        ast.parse(assets_src)

    def test_spark_assets_have_deprecated_suffix(self, assets_src):
        """The Spark-based gold assets must end in _deprecated (so
        Dagster doesn't pick them up as active assets).
        """
        for asset in ["gold_market_dominance", "gold_volatility_ranking",
                       "gold_movers_ranking", "gold_momentum_indicators"]:
            pattern = rf"def {asset}_deprecated\("
            assert re.search(pattern, assets_src), (
                f"Asset {asset} must be renamed to *_deprecated and "
                f"have its @asset decorator removed"
            )
            # Make sure the @asset decorator is NOT present above it
            # (i.e. the @asset line for these is commented out)
            uncommented = re.search(
                rf"^@asset\([^)]*\).*?\n\s*def {asset}\(",
                assets_src, re.MULTILINE | re.DOTALL,
            )
            assert not uncommented, (
                f"Asset {asset} still has active @asset decorator; "
                f"comment it out"
            )

    def test_gold_advanced_job_uses_trino_only(self, assets_src):
        """The gold_advanced_job selection must NOT include any of the
        deprecated Spark assets (comments are OK; actual entries are not).
        """
        # Find the job's selection block
        m = re.search(
            r"gold_advanced_job\s*=\s*define_asset_job\([^)]*?selection=\[([^\]]+)\]",
            assets_src, re.DOTALL,
        )
        assert m, "Could not find gold_advanced_job selection"
        selection = m.group(1)
        # Strip line-level comments so we only inspect uncommented code.
        active_lines = [
            line for line in selection.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        active_selection = "\n".join(active_lines)
        for asset in ["gold_market_dominance", "gold_volatility_ranking",
                       "gold_movers_ranking", "gold_momentum_indicators"]:
            assert asset not in active_selection, (
                f"gold_advanced_job still actively selects {asset} — "
                f"should be removed (comments are OK)"
            )
        # compute_gold_layer is kept for back-compat
        assert "compute_gold_layer" in active_selection

    def test_canonical_path_is_gold_layer_job(self, assets_src):
        """The Trino job is in gold_layer_job (already correct, no change)."""
        m = re.search(
            r"gold_layer_job\s*=\s*define_asset_job\([^)]*?selection=\[([^\]]+)\]",
            assets_src, re.DOTALL,
        )
        assert m
        selection = m.group(1)
        assert "compute_gold_layer" in selection
        assert "compute_news_sentiment_daily" in selection


# ── API alignment tests ─────────────────────────────────────────────────────


class TestMarketOverviewApiAlignment:
    """The API must query the canonical gold_* tables (not Spark tables)."""

    @pytest.fixture
    def api_src(self):
        path = REPO / "backend" / "api" / "market_overview.py"
        return path.read_text(encoding="utf-8")

    def test_api_queries_canonical_tables_only(self, api_src):
        """The SQL must reference ``gold_*`` (Trino canonical) and must
        NOT reference any deprecated Spark-only table.
        """
        # All from() calls reference the schema
        from_pattern = r"FROM\s+\{DB\}\.(\w+)"
        for m in re.finditer(from_pattern, api_src):
            table = m.group(1)
            assert table.startswith("gold_"), (
                f"API queries non-canonical table {{DB}}.{table} — "
                f"should be in CANONICAL_GOLD_TABLES"
            )
        # Negative check: deprecated Spark-only tables must not appear
        for bad in ["market_dominance", "volatility_ranking",
                     "movers_ranking", "gold_market_overview",
                     "gold_symbol_stats_daily"]:
            assert f"{{DB}}.{bad}" not in api_src, (
                f"API still queries deprecated table {bad}"
            )
        # gold_sector_performance IS in canonical (with computed_at col),
        # so it's allowed even though there's a Spark version of the
        # same name.

    def test_api_uses_freshness_filter(self, api_src):
        """Every query that reads gold tables should filter on
        computed_at to enable the freshness fallback.
        """
        # Non-greedy match: stop at the next triple-quote or the
        # next FROM clause. We split by f-string boundaries and then
        # look at the SQL text inside.
        # Approach: find every FROM {DB}.gold_* occurrence and the
        # 200 chars after it to check for computed_at.
        gold_refs = list(re.finditer(r"FROM\s+\{DB\}\.(gold_\w+)", api_src))
        assert len(gold_refs) >= 5, (
            f"Expected at least 5 gold queries, found {len(gold_refs)}"
        )
        for m in gold_refs:
            # Look at the next 300 chars after the match for a filter
            after = api_src[m.end():m.end() + 300]
            assert "computed_at" in after or "date" in after, (
                f"Gold query on {m.group(1)} missing freshness filter"
            )

    def test_api_imports_manifest(self, api_src):
        """Verify the manifest import is present and tolerant of failure."""
        assert "from src.lakehouse.gold_schema_manifest" in api_src or \
               "from lakehouse.gold_schema_manifest" in api_src
        # The import must be in a try/except (defensive)
        assert "try:" in api_src
        assert "except" in api_src
