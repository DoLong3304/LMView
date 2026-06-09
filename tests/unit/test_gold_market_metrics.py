"""Unit tests for src.lakehouse.gold.market_metrics.

Tests cover:
- Table names use iceberg.crypto_lakehouse (not iceberg_catalog.gold)
- GoldMarketDominance: table config, create_table SQL
- GoldVolatilityRanking: table config, create_table SQL
- GoldMoversRanking: table config, create_table SQL
- GoldMarketOverview (aggregations.py): catalog references
- GoldNewsSentiment (news_aggregations.py): catalog references

NOTE: pyspark is not installed locally, so we mock it via sys.modules patches.
"""
import sys
import types
import pytest
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Mock pyspark before any lakehouse import
# ---------------------------------------------------------------------------

def _create_mock_pyspark():
    """Create a mock pyspark module tree."""
    mock_spark = types.ModuleType("pyspark")
    mock_sql = types.ModuleType("pyspark.sql")
    mock_functions = MagicMock()
    mock_session_cls = MagicMock()
    mock_session_cls.builder = MagicMock()
    mock_window = MagicMock()
    mock_types_mod = MagicMock()

    # SparkSession.builder.config().getOrCreate() → returns MagicMock
    mock_session_cls.builder.config.return_value = mock_session_cls.builder
    mock_session_cls.builder.getOrCreate.return_value = MagicMock()

    mock_spark.sql = mock_sql
    mock_sql.SparkSession = mock_session_cls
    mock_sql.functions = mock_functions
    mock_sql.window = mock_window
    mock_sql.types = mock_types_mod

    sys.modules["pyspark"] = mock_spark
    sys.modules["pyspark.sql"] = mock_sql
    sys.modules["pyspark.sql.functions"] = mock_functions
    sys.modules["pyspark.sql.window"] = mock_window
    sys.modules["pyspark.sql.types"] = mock_types_mod

    return mock_spark


# Install mock before import
_pyspark_mock = _create_mock_pyspark()


# ---------------------------------------------------------------------------
# Tests: Catalog references (Phase D verification)
# ---------------------------------------------------------------------------

class TestCatalogReferences:
    """Verify no iceberg_catalog.gold references remain in market_metrics."""

    @pytest.mark.unit
    def test_market_dominance_gold_table(self):
        from src.lakehouse.gold.market_metrics import GoldMarketDominance
        mock_spark = MagicMock()
        obj = GoldMarketDominance(mock_spark)
        assert "iceberg.crypto_lakehouse" in obj.gold_table
        assert "iceberg_catalog" not in obj.gold_table

    @pytest.mark.unit
    def test_market_dominance_ticker_table(self):
        from src.lakehouse.gold.market_metrics import GoldMarketDominance
        mock_spark = MagicMock()
        obj = GoldMarketDominance(mock_spark)
        assert "iceberg.crypto_lakehouse" in obj.ticker_table
        assert "iceberg_catalog" not in obj.ticker_table

    @pytest.mark.unit
    def test_volatility_gold_table(self):
        from src.lakehouse.gold.market_metrics import GoldVolatilityRanking
        mock_spark = MagicMock()
        obj = GoldVolatilityRanking(mock_spark)
        assert "iceberg.crypto_lakehouse" in obj.gold_table
        assert "iceberg_catalog" not in obj.gold_table

    @pytest.mark.unit
    def test_movers_gold_table(self):
        from src.lakehouse.gold.market_metrics import GoldMoversRanking
        mock_spark = MagicMock()
        obj = GoldMoversRanking(mock_spark)
        assert "iceberg.crypto_lakehouse" in obj.gold_table
        assert "iceberg_catalog" not in obj.gold_table


# ---------------------------------------------------------------------------
# Tests: GoldMarketDominance
# ---------------------------------------------------------------------------

class TestGoldMarketDominance:
    @pytest.mark.unit
    def test_gold_table_name(self):
        from src.lakehouse.gold.market_metrics import GoldMarketDominance
        mock_spark = MagicMock()
        obj = GoldMarketDominance(mock_spark)
        assert obj.gold_table == "iceberg.crypto_lakehouse.market_dominance"

    @pytest.mark.unit
    def test_create_table_uses_crypto_lakehouse(self):
        from src.lakehouse.gold.market_metrics import GoldMarketDominance
        mock_spark = MagicMock()
        obj = GoldMarketDominance(mock_spark)
        obj.create_table()
        sql_call = mock_spark.sql.call_args[0][0]
        assert "iceberg.crypto_lakehouse.market_dominance" in sql_call
        assert "iceberg_catalog" not in sql_call

    @pytest.mark.unit
    def test_create_table_has_partitioning(self):
        from src.lakehouse.gold.market_metrics import GoldMarketDominance
        mock_spark = MagicMock()
        obj = GoldMarketDominance(mock_spark)
        obj.create_table()
        sql_call = mock_spark.sql.call_args[0][0]
        assert "PARTITIONED BY" in sql_call

    @pytest.mark.unit
    def test_create_table_has_btc_eth_dominance_columns(self):
        from src.lakehouse.gold.market_metrics import GoldMarketDominance
        mock_spark = MagicMock()
        obj = GoldMarketDominance(mock_spark)
        obj.create_table()
        sql_call = mock_spark.sql.call_args[0][0]
        assert "btc_dominance_pct" in sql_call
        assert "eth_dominance_pct" in sql_call


# ---------------------------------------------------------------------------
# Tests: GoldVolatilityRanking
# ---------------------------------------------------------------------------

class TestGoldVolatilityRanking:
    @pytest.mark.unit
    def test_gold_table_name(self):
        from src.lakehouse.gold.market_metrics import GoldVolatilityRanking
        mock_spark = MagicMock()
        obj = GoldVolatilityRanking(mock_spark)
        assert obj.gold_table == "iceberg.crypto_lakehouse.volatility_ranking"

    @pytest.mark.unit
    def test_create_table_uses_crypto_lakehouse(self):
        from src.lakehouse.gold.market_metrics import GoldVolatilityRanking
        mock_spark = MagicMock()
        obj = GoldVolatilityRanking(mock_spark)
        obj.create_table()
        sql_call = mock_spark.sql.call_args[0][0]
        assert "iceberg.crypto_lakehouse.volatility_ranking" in sql_call
        assert "iceberg_catalog" not in sql_call

    @pytest.mark.unit
    def test_create_table_has_volatility_columns(self):
        from src.lakehouse.gold.market_metrics import GoldVolatilityRanking
        mock_spark = MagicMock()
        obj = GoldVolatilityRanking(mock_spark)
        obj.create_table()
        sql_call = mock_spark.sql.call_args[0][0]
        assert "volatility_1h" in sql_call
        assert "volatility_24h" in sql_call
        assert "volatility_7d" in sql_call
        assert "rank_by_volatility" in sql_call


# ---------------------------------------------------------------------------
# Tests: GoldMoversRanking
# ---------------------------------------------------------------------------

class TestGoldMoversRanking:
    @pytest.mark.unit
    def test_gold_table_name(self):
        from src.lakehouse.gold.market_metrics import GoldMoversRanking
        mock_spark = MagicMock()
        obj = GoldMoversRanking(mock_spark)
        assert obj.gold_table == "iceberg.crypto_lakehouse.movers_ranking"

    @pytest.mark.unit
    def test_create_table_uses_crypto_lakehouse(self):
        from src.lakehouse.gold.market_metrics import GoldMoversRanking
        mock_spark = MagicMock()
        obj = GoldMoversRanking(mock_spark)
        obj.create_table()
        sql_call = mock_spark.sql.call_args[0][0]
        assert "iceberg.crypto_lakehouse.movers_ranking" in sql_call
        assert "iceberg_catalog" not in sql_call

    @pytest.mark.unit
    def test_create_table_has_gainer_loser_columns(self):
        from src.lakehouse.gold.market_metrics import GoldMoversRanking
        mock_spark = MagicMock()
        obj = GoldMoversRanking(mock_spark)
        obj.create_table()
        sql_call = mock_spark.sql.call_args[0][0]
        assert "category" in sql_call
        assert "change_pct" in sql_call
        assert "timeframe" in sql_call
        assert "volume_24h" in sql_call


# ---------------------------------------------------------------------------
# Tests: Gold aggregations (aggregations.py + news_aggregations.py) catalogs
# ---------------------------------------------------------------------------

class TestGoldAggregationsCatalog:
    """Verify all gold aggregation modules use correct catalog."""

    @pytest.mark.unit
    def test_aggregations_gold_table(self):
        from src.lakehouse.gold.aggregations import GoldMarketOverview
        mock_spark = MagicMock()
        obj = GoldMarketOverview(mock_spark)
        assert "iceberg.crypto_lakehouse" in obj.gold_table
        assert "iceberg_catalog" not in obj.gold_table

    @pytest.mark.unit
    def test_aggregations_silver_table(self):
        from src.lakehouse.gold.aggregations import GoldMarketOverview
        mock_spark = MagicMock()
        obj = GoldMarketOverview(mock_spark)
        assert "iceberg.crypto_lakehouse" in obj.silver_table

    @pytest.mark.unit
    def test_news_aggregations_gold_table(self):
        from src.lakehouse.gold.news_aggregations import GoldNewsSentiment
        mock_spark = MagicMock()
        obj = GoldNewsSentiment(mock_spark)
        assert "iceberg.crypto_lakehouse" in obj.gold_table
        assert "iceberg_catalog" not in obj.gold_table

    @pytest.mark.unit
    def test_news_aggregations_silver_table(self):
        from src.lakehouse.gold.news_aggregations import GoldNewsSentiment
        mock_spark = MagicMock()
        obj = GoldNewsSentiment(mock_spark)
        assert "iceberg.crypto_lakehouse" in obj.silver_table
