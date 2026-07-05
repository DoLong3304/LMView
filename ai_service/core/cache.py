"""In-memory LRU response cache for common AI queries.

Reduces latency for repeated questions about the same symbol/timeframe
by caching the LLM response. Entries expire after a TTL.

Cache key: (message_normalized, symbol, timeframe, indicators_sorted, language, mode)
TTL: 30s for price/market queries, 5min for educational/knowledge queries.
Max entries: 100 (LRU eviction).
"""
from __future__ import annotations

import hashlib
import logging
import time
import re
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("ai_service.core.cache")

# Cache config
_MAX_ENTRIES = 500
_TTL_PRICE = 120       # seconds: price/market queries (was 30)
_TTL_EDUCATION = 600  # seconds: educational/knowledge queries (was 300)

_QUESTION_TYPE_PRICE = re.compile(
    r"\b(price|current|now|value|cost|worth|rate|how much|what is .+ price)\b",
    re.IGNORECASE,
)
_QUESTION_TYPE_MARKET = re.compile(
    r"\b(market|volume|order book|bid|ask|spread|overview|gainers|losers)\b",
    re.IGNORECASE,
)

# ── Cache storage ───────────────────────────────────────────────────────────

_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()

# ── Public API ──────────────────────────────────────────────────────────────

def make_cache_key(
    message: str,
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    indicators: Optional[List[str]] = None,
    language: Optional[str] = None,
    mode: str = "ask",
) -> str:
    """Build a deterministic cache key from request parameters.

    Normalizes the message (lowercase, collapse whitespace), sorts
    indicator names, and hashes the result for compact keys.
    """
    norm = message.lower().strip()
    norm = re.sub(r"\s+", " ", norm)  # collapse whitespace
    norm = re.sub(r"[^\w\s]", "", norm)  # strip punctuation

    parts = [norm]
    if symbol:
        parts.append(symbol.upper())
    if timeframe:
        parts.append(timeframe.lower())
    if indicators:
        parts.append(",".join(sorted(i.lower() for i in indicators if i)))
    if language:
        parts.append(language.lower())
    parts.append(mode)

    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _classify_question_type(message: str) -> str:
    """Classify question as 'price', 'market', or 'educational'."""
    if _QUESTION_TYPE_PRICE.search(message):
        return "price"
    if _QUESTION_TYPE_MARKET.search(message):
        return "market"
    return "educational"


def get_from_cache(key: str, message: str) -> Optional[Dict[str, Any]]:
    """Look up a cached response. Returns None if miss or expired."""
    entry = _cache.get(key)
    if entry is None:
        return None

    elapsed = time.time() - entry["timestamp"]
    qtype = entry.get("question_type") or _classify_question_type(message)
    ttl = _TTL_PRICE if qtype in ("price", "market") else _TTL_EDUCATION

    if elapsed > ttl:
        _cache.pop(key, None)
        logger.debug("Cache miss (expired): %s (%.1fs > %ds)", key[:12], elapsed, ttl)
        return None

    # Move to end (recently used)
    _cache.move_to_end(key)
    logger.debug("Cache hit: %s (%.1fs old, type=%s)", key[:12], elapsed, qtype)
    return entry["data"]


def set_in_cache(key: str, data: Dict[str, Any], message: str) -> None:
    """Store a response in the cache with current timestamp."""
    if len(_cache) >= _MAX_ENTRIES:
        _cache.popitem(last=False)  # evict LRU

    _cache[key] = {
        "timestamp": time.time(),
        "data": data,
        "question_type": _classify_question_type(message),
    }
    logger.debug("Cache set: %s (size=%d)", key[:12], len(_cache))


def invalidate_cache(symbol: Optional[str] = None) -> int:
    """Invalidate cache entries, optionally by symbol.

    Returns count of invalidated entries.
    """
    if not symbol:
        count = len(_cache)
        _cache.clear()
        logger.info("Cache cleared (%d entries)", count)
        return count

    prefix = symbol.upper()
    keys = [k for k in _cache if prefix in k]
    for k in keys:
        _cache.pop(k, None)
    logger.info("Cache invalidated for %s (%d entries)", prefix, len(keys))
    return len(keys)


def cache_stats() -> Dict[str, Any]:
    """Return cache statistics."""
    return {
        "size": len(_cache),
        "max_size": _MAX_ENTRIES,
        "entries": [
            {
                "key": k[:16] + "...",
                "age_s": round(time.time() - v["timestamp"], 1),
                "question_type": v.get("question_type", "unknown"),
            }
            for k, v in list(_cache.items())[-10:]  # last 10
        ],
    }
