"""
News context builder — assembles compact news context for AI Ask/Interact mode.

Pulls relevant news from PostgreSQL persistence (not live web calls).
Ranks articles by symbol relevance, recency, sentiment strength, and source count.
Generates data caveats about news availability and freshness.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from backend.core.postgres import get_pg_pool

logger = logging.getLogger("ai_service.context.news_context")

# ── Configuration ─────────────────────────────────────────────────────────────

MAX_HEADLINES_IN_PROMPT = 8
MAX_ARTICLE_QUERY_LIMIT = 50
DEFAULT_LOOKBACK_HOURS = 24
STALE_NEWS_HOURS = 12
SPARSE_ARTICLE_THRESHOLD = 3
STRONG_SENTIMENT_THRESHOLD = 0.3
HIGH_SENTIMENT_THRESHOLD = 0.5

# Source reliability tiers (higher = more reliable)
SOURCE_RELIABILITY: Dict[str, float] = {
    "coindesk": 0.9,
    "cointelegraph": 0.85,
    "theblock": 0.85,
    "decrypt": 0.8,
    "bitcoinmagazine": 0.8,
    "cryptoslate": 0.75,
    "newsbtc": 0.7,
    "coingape": 0.65,
    "ambcrypto": 0.6,
    "cryptopotato": 0.6,
    "u.today": 0.6,
    "beincrypto": 0.6,
}
DEFAULT_SOURCE_RELIABILITY = 0.5


# ── Data types ────────────────────────────────────────────────────────────────

class NewsContextResult:
    """Compact news context result for AI prompts."""

    def __init__(
        self,
        symbol: Optional[str],
        article_count: int,
        source_count: int,
        top_headlines: List[Dict[str, Any]],
        sentiment_summary: Dict[str, Any],
        freshness: Dict[str, Any],
        risk_events: List[str],
        caveats: List[str],
        trending_symbols: List[Dict[str, Any]],
    ):
        self.symbol = symbol
        self.article_count = article_count
        self.source_count = source_count
        self.top_headlines = top_headlines
        self.sentiment_summary = sentiment_summary
        self.freshness = freshness
        self.risk_events = risk_events
        self.caveats = caveats
        self.trending_symbols = trending_symbols

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for JSON response / prompt embedding."""
        return {
            "symbol": self.symbol,
            "article_count": self.article_count,
            "source_count": self.source_count,
            "top_headlines": self.top_headlines,
            "sentiment_summary": self.sentiment_summary,
            "freshness": self.freshness,
            "risk_events": self.risk_events,
            "caveats": self.caveats,
            "trending_symbols": self.trending_symbols,
        }


# ── Public API ────────────────────────────────────────────────────────────────

async def build_news_context(
    symbol: Optional[str] = None,
    query: Optional[str] = None,
    hours: int = DEFAULT_LOOKBACK_HOURS,
) -> NewsContextResult:
    """
    Build compact news context for AI analysis.

    Args:
        symbol: Target symbol (e.g., 'BTCUSDT'). Normalizes to base symbol.
        query: Optional user query text for keyword relevance scoring.
        hours: Lookback window in hours.

    Returns:
        NewsContextResult with ranked headlines, sentiment summary, and caveats.
    """
    pool = await get_pg_pool()
    if pool is None:
        return _empty_result(symbol, ["News database unavailable."])

    symbol_norm = _normalize_symbol(symbol)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    try:
        async with pool.acquire() as conn:
            # Symbol-specific articles
            symbol_articles = []
            if symbol_norm:
                symbol_articles = await _fetch_symbol_articles(conn, symbol_norm, cutoff)

            # Market-wide trending articles
            trending_articles = await _fetch_trending_articles(conn, cutoff)

            # Trending symbols
            trending_symbols = await _fetch_trending_symbols(conn, cutoff)

        # Deduplicate articles (symbol-specific may overlap with trending)
        all_articles = _deduplicate_articles(symbol_articles, trending_articles)

        if not all_articles:
            return _empty_result(symbol_norm, ["No relevant news found in the last {0} hours.".format(hours)])

        # Rank articles
        ranked = _rank_articles(
            articles=all_articles,
            target_symbol=symbol_norm,
            query=query,
        )

        # Build context components
        top_headlines = _extract_top_headlines(ranked[:MAX_HEADLINES_IN_PROMPT])
        sentiment_summary = _compute_sentiment_summary(ranked, symbol_norm)
        freshness = _compute_freshness(ranked)
        risk_events = _identify_risk_events(ranked, symbol_norm)
        caveats = _generate_caveats(
            articles=ranked,
            symbol=symbol_norm,
            freshness=freshness,
            sentiment_summary=sentiment_summary,
        )
        source_count = len(set(a.get("source", "") for a in ranked))

        return NewsContextResult(
            symbol=symbol_norm,
            article_count=len(ranked),
            source_count=source_count,
            top_headlines=top_headlines,
            sentiment_summary=sentiment_summary,
            freshness=freshness,
            risk_events=risk_events,
            caveats=caveats,
            trending_symbols=trending_symbols,
        )

    except Exception as exc:
        logger.warning("News context build failed: %s", exc)
        return _empty_result(symbol_norm, [f"News context unavailable: {str(exc)[:100]}"])


# ── Database queries ──────────────────────────────────────────────────────────

async def _fetch_symbol_articles(conn, symbol_norm: str, cutoff: datetime) -> List[Dict[str, Any]]:
    """Fetch articles mentioning the target symbol."""
    rows = await conn.fetch(
        """
        SELECT id, source, title, summary, content_snippet,
               published_at, sentiment_score, sentiment_label,
               sentiment_confidence, symbols_mentioned, url
        FROM news_articles
        WHERE published_at >= $1
          AND $2 = ANY(symbols_mentioned)
        ORDER BY published_at DESC
        LIMIT $3
        """,
        cutoff, symbol_norm, MAX_ARTICLE_QUERY_LIMIT,
    )
    return [dict(row) for row in rows]


async def _fetch_trending_articles(conn, cutoff: datetime) -> List[Dict[str, Any]]:
    """Fetch market-wide trending articles (strong sentiment or recent)."""
    rows = await conn.fetch(
        """
        SELECT id, source, title, summary, content_snippet,
               published_at, sentiment_score, sentiment_label,
               sentiment_confidence, symbols_mentioned, url
        FROM news_articles
        WHERE published_at >= $1
        ORDER BY abs(coalesce(sentiment_score, 0)) DESC, published_at DESC
        LIMIT $2
        """,
        cutoff, MAX_ARTICLE_QUERY_LIMIT,
    )
    return [dict(row) for row in rows]


async def _fetch_trending_symbols(conn, cutoff: datetime) -> List[Dict[str, Any]]:
    """Fetch trending symbols by mention count."""
    rows = await conn.fetch(
        """
        SELECT symbol, COUNT(*) AS mention_count,
               AVG(coalesce(sentiment_score, 0)) AS avg_sentiment
        FROM (
            SELECT unnest(symbols_mentioned) AS symbol, sentiment_score
            FROM news_articles
            WHERE published_at >= $1 AND symbols_mentioned IS NOT NULL
        ) s
        GROUP BY symbol
        ORDER BY mention_count DESC
        LIMIT 10
        """,
        cutoff,
    )
    return [
        {
            "symbol": row["symbol"],
            "mention_count": row["mention_count"],
            "avg_sentiment": round(float(row["avg_sentiment"] or 0), 3),
        }
        for row in rows
    ]


# ── Ranking ───────────────────────────────────────────────────────────────────

def _rank_articles(
    articles: List[Dict[str, Any]],
    target_symbol: Optional[str],
    query: Optional[str],
) -> List[Dict[str, Any]]:
    """
    Rank articles by composite score.

    Factors:
    1. Symbol match (exact > mentioned > market-wide)
    2. Recency (last 2h > 6h > 24h)
    3. Source reliability
    4. Sentiment strength
    5. Query keyword relevance
    """
    now = datetime.now(timezone.utc)

    for article in articles:
        score = 0.0

        # Symbol match
        symbols = article.get("symbols_mentioned") or []
        if target_symbol and target_symbol in symbols:
            score += 3.0
        elif target_symbol and any(s in (target_symbol[:3], target_symbol) for s in symbols):
            score += 1.5

        # Recency
        pub = article.get("published_at")
        if pub:
            if isinstance(pub, str):
                try:
                    pub = datetime.fromisoformat(pub)
                except (ValueError, TypeError):
                    pub = None
            if pub:
                age_hours = (now - pub).total_seconds() / 3600
                if age_hours < 2:
                    score += 2.0
                elif age_hours < 6:
                    score += 1.5
                elif age_hours < 12:
                    score += 1.0
                else:
                    score += 0.5

        # Source reliability
        source = (article.get("source") or "").lower()
        reliability = SOURCE_RELIABILITY.get(source, DEFAULT_SOURCE_RELIABILITY)
        score += reliability

        # Sentiment strength
        sentiment = abs(float(article.get("sentiment_score") or 0))
        if sentiment > STRONG_SENTIMENT_THRESHOLD:
            score += sentiment

        # Query keyword relevance
        if query:
            title = (article.get("title") or "").lower()
            query_lower = query.lower()
            keywords = query_lower.split()
            matched = sum(1 for kw in keywords if kw in title and len(kw) > 2)
            if matched > 0:
                score += min(2.0, matched * 0.5)

        article["_rank_score"] = score

    articles.sort(key=lambda a: a.get("_rank_score", 0), reverse=True)
    return articles


# ── Context extraction ────────────────────────────────────────────────────────

def _extract_top_headlines(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract compact headline entries for prompt inclusion."""
    headlines = []
    for article in articles:
        pub = article.get("published_at")
        pub_str = None
        if pub:
            if isinstance(pub, datetime):
                pub_str = pub.isoformat()
            elif isinstance(pub, str):
                pub_str = pub

        headlines.append({
            "title": (article.get("title") or "")[:200],
            "source": article.get("source") or "unknown",
            "sentiment": article.get("sentiment_label") or "neutral",
            "sentiment_score": round(float(article.get("sentiment_score") or 0), 3),
            "published_at": pub_str,
            "symbols": (article.get("symbols_mentioned") or [])[:5],
        })
    return headlines


def _compute_sentiment_summary(
    articles: List[Dict[str, Any]],
    symbol: Optional[str],
) -> Dict[str, Any]:
    """Compute aggregate sentiment stats."""
    scores = [float(a.get("sentiment_score") or 0) for a in articles]
    if not scores:
        return {
            "direction": "neutral",
            "avg_score": 0,
            "positive_count": 0,
            "neutral_count": 0,
            "negative_count": 0,
            "confidence": "none",
        }

    avg = sum(scores) / len(scores)
    positive = sum(1 for s in scores if s > 0.05)
    negative = sum(1 for s in scores if s < -0.05)
    neutral = len(scores) - positive - negative

    if avg > 0.1:
        direction = "bullish"
    elif avg < -0.1:
        direction = "bearish"
    else:
        direction = "neutral"

    # Confidence based on agreement and count
    if len(scores) >= 5 and abs(positive - negative) > len(scores) * 0.4:
        confidence = "moderate"
    elif len(scores) >= 10 and abs(positive - negative) > len(scores) * 0.6:
        confidence = "high"
    elif len(scores) < SPARSE_ARTICLE_THRESHOLD:
        confidence = "low"
    else:
        confidence = "low"

    return {
        "direction": direction,
        "avg_score": round(avg, 3),
        "positive_count": positive,
        "neutral_count": neutral,
        "negative_count": negative,
        "confidence": confidence,
        "symbol_specific": symbol is not None,
    }


def _compute_freshness(articles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute news freshness metadata."""
    now = datetime.now(timezone.utc)
    pub_times = []

    for article in articles:
        pub = article.get("published_at")
        if pub:
            if isinstance(pub, str):
                try:
                    pub = datetime.fromisoformat(pub)
                except (ValueError, TypeError):
                    continue
            if isinstance(pub, datetime):
                pub_times.append(pub)

    if not pub_times:
        return {
            "newest_age_hours": None,
            "oldest_age_hours": None,
            "is_stale": True,
        }

    newest = max(pub_times)
    oldest = min(pub_times)
    newest_age = (now - newest).total_seconds() / 3600
    oldest_age = (now - oldest).total_seconds() / 3600

    return {
        "newest_age_hours": round(newest_age, 1),
        "oldest_age_hours": round(oldest_age, 1),
        "newest_at": newest.isoformat(),
        "is_stale": newest_age > STALE_NEWS_HOURS,
    }


def _identify_risk_events(
    articles: List[Dict[str, Any]],
    symbol: Optional[str],
) -> List[str]:
    """Identify potential risk events from news headlines."""
    risk_keywords = {
        "hack", "hacked", "exploit", "vulnerability", "breach",
        "sec", "regulation", "ban", "lawsuit", "investigation",
        "crash", "collapse", "liquidat", "insolvent", "bankrupt",
        "delisting", "delist", "fraud", "scam",
        "fork", "halving", "upgrade",
    }
    risk_events = []

    for article in articles:
        title_lower = (article.get("title") or "").lower()
        symbols = article.get("symbols_mentioned") or []

        # Only flag risk events for target symbol or very strong market-wide events
        is_relevant = (
            (symbol and symbol in symbols)
            or abs(float(article.get("sentiment_score") or 0)) > HIGH_SENTIMENT_THRESHOLD
        )
        if not is_relevant:
            continue

        matched = [kw for kw in risk_keywords if kw in title_lower]
        if matched:
            risk_events.append(
                f"{article.get('title', 'Unknown')[:120]} "
                f"[{article.get('source', '?')}, {article.get('sentiment_label', '?')}]"
            )

    return risk_events[:5]  # Cap at 5 risk events


# ── Caveat generation ─────────────────────────────────────────────────────────

def _generate_caveats(
    articles: List[Dict[str, Any]],
    symbol: Optional[str],
    freshness: Dict[str, Any],
    sentiment_summary: Dict[str, Any],
) -> List[str]:
    """Generate data caveats about news context quality."""
    caveats = []

    if not articles:
        caveats.append("No relevant news found.")
        return caveats

    if len(articles) < SPARSE_ARTICLE_THRESHOLD:
        caveats.append(
            f"Only {len(articles)} article(s) found — sentiment may not be representative."
        )

    if freshness.get("is_stale"):
        age = freshness.get("newest_age_hours")
        if age is not None:
            caveats.append(
                f"Newest article is {age:.0f}h old — news context may not reflect current events."
            )

    if sentiment_summary.get("confidence") in ("low", "none"):
        caveats.append(
            "Sentiment confidence is low — do not rely on news sentiment alone."
        )

    # Always include the safety caveat
    caveats.append(
        "News sentiment is contextual information, not a trading signal or proof of causality."
    )

    return caveats


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalize_symbol(symbol: Optional[str]) -> Optional[str]:
    """Normalize symbol to base form (e.g., 'BTCUSDT' -> 'BTC')."""
    if not symbol:
        return None
    cleaned = symbol.upper().replace("USDT", "").replace("USD", "")
    return cleaned or None


def _deduplicate_articles(
    primary: List[Dict[str, Any]],
    secondary: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Merge and deduplicate two article lists by ID."""
    seen_ids = set()
    result = []

    for article in primary + secondary:
        article_id = str(article.get("id", ""))
        if article_id and article_id not in seen_ids:
            seen_ids.add(article_id)
            result.append(article)

    return result


def _empty_result(symbol: Optional[str], caveats: List[str]) -> NewsContextResult:
    """Return an empty NewsContextResult with caveats."""
    return NewsContextResult(
        symbol=symbol,
        article_count=0,
        source_count=0,
        top_headlines=[],
        sentiment_summary={
            "direction": "neutral",
            "avg_score": 0,
            "positive_count": 0,
            "neutral_count": 0,
            "negative_count": 0,
            "confidence": "none",
        },
        freshness={"newest_age_hours": None, "oldest_age_hours": None, "is_stale": True},
        risk_events=[],
        caveats=caveats,
        trending_symbols=[],
    )
