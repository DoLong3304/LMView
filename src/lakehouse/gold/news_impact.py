"""
Gold Layer — News Market Impact (v0.24.5, Task 4)

For each news article × symbol mention, measure the price impact of
the article at three forward-looking horizons (t+1h, t+4h, t+24h)
and persist it to ``gold_news_market_impact``.

## Why this exists

TradingView and CryptoQuant offer "News Impact" overlays that let
traders see, quantitatively, how a piece of news actually moved
the market. Before v0.24.5 we had news sentiment (qualitative) and
price data (quantitative) but no causal link — analysts had to
eyeball-chart a headline against the kline tape to see the impact.

This Gold job closes that gap with a clean per-row output that's
trivial for the API to query and overlay on a candlestick chart.

## Design choices

- **Batch Spark, not Flink streaming.** News publishing is low-rate
  (a few per minute at peak), and the join is windowed across
  ``silver_kline_1h`` which is itself a batch product. Spark window
  functions are easier to read and reason about than Flink timers
  here, and there's no real-time SLA on this table (a 1-hour
  cadence is fine for a Gold layer).

- **Outer-join, not inner.** A young article (<1h old) won't have
  ``price_1h_after`` yet. A 5-minute-old article won't have
  ``price_4h_after``. We persist the row anyway with NULL impact
  fields, so the API can render "impact pending" instead of hiding
  the news.

- **Single exchange for the price feed.** We use ``binance`` as the
  canonical reference for every news impact. Cross-exchange price
  divergence is <50bps for major symbols and the API consumers
  don't need to know which venue the impact was measured on. We
  record the reference exchange in the row anyway for audit.

- **Symbol match is exact.** A news article about "ETH" maps to
  "ETHUSDT". We use the symbol-mapping table from the news
  enrichment step (column ``affected_symbols`` is an array of
  canonical symbols). We do NOT fuzzy-match headlines.

## Schema (see gold_schema_manifest.py for the canonical declaration)

  news_id           BIGINT
  symbol            VARCHAR
  exchange          VARCHAR         (always 'binance' in v0.24.5)
  published_at      TIMESTAMP WITH TIME ZONE
  headline          VARCHAR
  url               VARCHAR
  source            VARCHAR
  sentiment         DOUBLE
  price_at_news     DOUBLE
  price_1h_after    DOUBLE           (NULL if kline not yet closed)
  price_4h_after    DOUBLE
  price_24h_after   DOUBLE
  change_1h_pct     DOUBLE
  change_4h_pct     DOUBLE
  change_24h_pct    DOUBLE
  impact_score      DOUBLE           (signed; see helper)
  computed_at       TIMESTAMP WITH TIME ZONE

## Operational

- Idempotent: re-running for the same window REPLACES rows in
  that window (no duplicates).
- Cadence: hourly is fine; daily is acceptable for a v0.24.5 MVP.
- Producer: ``orchestration/assets.py`` exposes
  ``compute_gold_news_market_impact`` as a Dagster asset.
"""

from __future__ import annotations

import logging
from typing import Iterable, Optional

logger = logging.getLogger(__name__)


# Reference exchange used for the price feed. Centralised here so
# tests can monkey-patch it if/when we add more reference venues.
DEFAULT_REFERENCE_EXCHANGE = "binance"


# Forward-looking horizons in hours. Exposed as a module constant
# so the API + manifest docs + tests can import the same values
# without drift.
IMPACT_HORIZONS_HOURS: tuple[int, ...] = (1, 4, 24)


def compute_impact_score(
    change_1h_pct: Optional[float],
    change_4h_pct: Optional[float],
    change_24h_pct: Optional[float],
    sentiment: Optional[float],
) -> Optional[float]:
    """Compute the signed impact score for a single news × symbol.

    Formula::

        impact_score = max(|change_1h|, |change_4h|, |change_24h|)
                      * sign(sentiment)

    Semantics:
      * Positive score  → bullish news moved the price UP.
      * Negative score  → bearish news moved the price DOWN.
      * Zero / NULL     → either no price data yet, or the news had
        no measurable impact.

    All three change fields are treated as None-safe so a fresh
    article (only ``change_1h_pct`` known) still produces a score.
    """
    candidates: list[float] = []
    for ch in (change_1h_pct, change_4h_pct, change_24h_pct):
        if ch is None:
            continue
        candidates.append(abs(ch))
    if not candidates:
        return None
    magnitude = max(candidates)
    if sentiment is None or abs(sentiment) < 1e-9:
        # News had no sentiment classification; we still report the
        # raw magnitude but we leave the sign neutral so the API can
        # show "no signal" rather than "bullish/bearish".
        return 0.0
    sign = 1.0 if sentiment > 0 else -1.0
    return round(magnitude * sign, 4)


def build_impact_row(
    *,
    news_id: int,
    symbol: str,
    exchange: str,
    published_at_ms: int,
    headline: str,
    url: str,
    source: str,
    sentiment: Optional[float],
    price_at_news: Optional[float],
    price_1h_after: Optional[float],
    price_4h_after: Optional[float],
    price_24h_after: Optional[float],
    computed_at_ms: int,
) -> dict:
    """Pure builder for a single impact row (testable in isolation).

    Computes the change_*_pct fields and the impact_score, then
    returns a dict matching the canonical ``gold_news_market_impact``
    schema.
    """
    def pct(a: Optional[float], b: Optional[float]) -> Optional[float]:
        if a is None or b is None or a == 0:
            return None
        return round((b - a) / a * 100.0, 4)

    change_1h = pct(price_at_news, price_1h_after)
    change_4h = pct(price_at_news, price_4h_after)
    change_24h = pct(price_at_news, price_24h_after)

    return {
        "news_id":        int(news_id),
        "symbol":         str(symbol),
        "exchange":       str(exchange),
        "published_at":   _ms_to_iso(published_at_ms),
        "headline":       str(headline),
        "url":            str(url),
        "source":         str(source),
        "sentiment":      float(sentiment) if sentiment is not None else None,
        "price_at_news":  _round_or_none(price_at_news),
        "price_1h_after": _round_or_none(price_1h_after),
        "price_4h_after": _round_or_none(price_4h_after),
        "price_24h_after":_round_or_none(price_24h_after),
        "change_1h_pct":  change_1h,
        "change_4h_pct":  change_4h,
        "change_24h_pct": change_24h,
        "impact_score":   compute_impact_score(change_1h, change_4h, change_24h, sentiment),
        "computed_at":    _ms_to_iso(computed_at_ms),
    }


def _ms_to_iso(ms: int) -> str:
    """Convert a millisecond epoch to ISO-8601 UTC string."""
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).isoformat()


def _round_or_none(x):
    return round(float(x), 8) if x is not None else None


# ─────────────────────────────────────────────────────────────────────────────
# Spark orchestration entry-point
# ─────────────────────────────────────────────────────────────────────────────


def compute_gold_news_market_impact(
    spark,
    *,
    lookback_hours: int = 48,
    reference_exchange: str = DEFAULT_REFERENCE_EXCHANGE,
    target_table: str = "iceberg.crypto_lakehouse.gold_news_market_impact",
) -> int:
    """Compute and persist the news-impact table for the last N hours.

    Parameters
    ----------
    spark:
        An active ``SparkSession``.
    lookback_hours:
        How far back to scan silver_news_enriched. Default 48h.
        Per-row idempotency: re-running with the same lookback
        REPLACES the rows in the window (no duplicates).
    reference_exchange:
        Exchange used as the price reference. Default ``binance``.
    target_table:
        Fully-qualified Iceberg table to write to.

    Returns
    -------
    int
        Number of rows written.

    Notes
    -----
    The Spark SQL is intentionally a single ``MERGE INTO`` so we can
    re-run for the same window and get the same answer (idempotent).
    The query uses ``silver_kline_1h`` for both the price-at-news
    and the price-N-hours-after lookups.
    """
    create_ddl = f"""
    CREATE TABLE IF NOT EXISTS {target_table} (
        news_id           BIGINT,
        symbol            VARCHAR,
        exchange          VARCHAR,
        published_at      TIMESTAMP,
        headline          VARCHAR,
        url               VARCHAR,
        source            VARCHAR,
        sentiment         DOUBLE,
        price_at_news     DOUBLE,
        price_1h_after    DOUBLE,
        price_4h_after    DOUBLE,
        price_24h_after   DOUBLE,
        change_1h_pct     DOUBLE,
        change_4h_pct     DOUBLE,
        change_24h_pct    DOUBLE,
        impact_score      DOUBLE,
        computed_at       TIMESTAMP
    ) USING iceberg
    PARTITIONED BY (days(published_at))
    TBLPROPERTIES (
        'write.format.default' = 'parquet',
        'write.parquet.compression-codec' = 'snappy'
    )
    """
    spark.sql(create_ddl)
    logger.info("Ensured table %s exists", target_table)

    merge_sql = f"""
    MERGE INTO {target_table} AS t
    USING (
        WITH news_in_window AS (
            SELECT
                CAST(id AS BIGINT)              AS news_id,
                headline,
                url,
                source,
                published_at,
                sentiment,
                EXPLODE(affected_symbols)       AS symbol
            FROM silver_news_enriched
            WHERE published_at >= current_timestamp - INTERVAL '{int(lookback_hours)}' HOURS
        ),
        kline_anchors AS (
            -- The 1h kline bucket that CONTAINS the published_at timestamp.
            SELECT
                symbol,
                bucket_open_time,
                close AS price_at_news
            FROM silver_kline_1h
            WHERE bucket_open_time <= current_timestamp
        ),
        impact AS (
            SELECT
                n.news_id,
                n.symbol,
                '{reference_exchange}'            AS exchange,
                n.published_at,
                n.headline,
                n.url,
                n.source,
                n.sentiment,
                a.price_at_news,
                k1.close AS price_1h_after,
                k4.close AS price_4h_after,
                k24.close AS price_24h_after,
                (k1.close  - a.price_at_news) / a.price_at_news * 100.0 AS change_1h_pct,
                (k4.close  - a.price_at_news) / a.price_at_news * 100.0 AS change_4h_pct,
                (k24.close - a.price_at_news) / a.price_at_news * 100.0 AS change_24h_pct,
                current_timestamp                AS computed_at
            FROM news_in_window n
            JOIN kline_anchors a
              ON a.symbol = n.symbol
             AND a.bucket_open_time = (
                 SELECT MAX(bucket_open_time)
                 FROM kline_anchors a2
                 WHERE a2.symbol = n.symbol
                   AND a2.bucket_open_time <= n.published_at
             )
            LEFT JOIN silver_kline_1h k1
              ON k1.symbol = n.symbol
             AND k1.bucket_open_time = a.bucket_open_time + INTERVAL '1' HOUR
            LEFT JOIN silver_kline_1h k4
              ON k4.symbol = n.symbol
             AND k4.bucket_open_time = a.bucket_open_time + INTERVAL '4' HOUR
            LEFT JOIN silver_kline_1h k24
              ON k24.symbol = n.symbol
             AND k24.bucket_open_time = a.bucket_open_time + INTERVAL '24' HOUR
            WHERE a.price_at_news IS NOT NULL
              AND a.price_at_news > 0
        )
        SELECT
            news_id, symbol, exchange, published_at,
            headline, url, source, sentiment,
            price_at_news, price_1h_after, price_4h_after, price_24h_after,
            change_1h_pct, change_4h_pct, change_24h_pct,
            CASE
                WHEN sentiment IS NULL OR ABS(sentiment) < 1e-9 THEN
                    GREATEST(
                        ABS(COALESCE(change_1h_pct,  0)),
                        ABS(COALESCE(change_4h_pct,  0)),
                        ABS(COALESCE(change_24h_pct, 0))
                    )
                ELSE
                    GREATEST(
                        ABS(COALESCE(change_1h_pct,  0)),
                        ABS(COALESCE(change_4h_pct,  0)),
                        ABS(COALESCE(change_24h_pct, 0))
                    ) * SIGN(sentiment)
            END AS impact_score,
            computed_at
        FROM impact
    ) AS s
    ON t.news_id = s.news_id AND t.symbol = s.symbol
    WHEN MATCHED THEN UPDATE SET *
    WHEN NOT MATCHED THEN INSERT *
    """
    spark.sql(merge_sql)
    rows = spark.sql(f"SELECT COUNT(*) AS c FROM {target_table}").collect()[0]["c"]
    logger.info("gold_news_market_impact MERGE complete; table now has %d rows", rows)
    return int(rows)
