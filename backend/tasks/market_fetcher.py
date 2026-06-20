"""
Background tasks:
1. Market metrics from gold layer (Trino, every 5 min)
2. Real-time Binance price poller (REST, every 500ms) for low-latency ticker
"""
import asyncio
import logging
import time
from datetime import datetime
from typing import List, Dict
import aiohttp

from backend.core.database import get_trino_connection, get_redis_master
from backend.services import market_service

logger = logging.getLogger(__name__)

# ── Real-time Binance price poller ───────────────────────────────────────

class BinancePricePoller:
    """Fetches ALL symbols price from Binance REST /ticker/price (~2s), writes to Redis.
    
    Protocol: Binance GET /api/v3/ticker/price (weight=2, returns ALL symbols).
    4 workers × 1 req/2s × 2 weight = 4 weight/s = 240 weight/min << 1200 limit.
    """

    ALL_PRICE_URL = "https://api.binance.com/api/v3/ticker/price"
    POLL_INTERVAL = 1.0  # seconds (4 workers × 2 weight = 480/min < 1200 limit)

    def __init__(self):
        self.task = None
        self.running = False
        self._session = None

    async def start(self):
        if self.running:
            return
        self.running = True
        self.task = asyncio.create_task(self._run())
        logger.info("[PricePoller] started (interval=%.1fs, all symbols via %s)",
                    self.POLL_INTERVAL, self.ALL_PRICE_URL)

    async def stop(self):
        if not self.running:
            return
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("[PricePoller] stopped")

    async def _run(self):
        await asyncio.sleep(2)
        while self.running:
            try:
                await self._poll()
            except Exception as e:
                logger.warning("[PricePoller] error: %s", e)
            await asyncio.sleep(self.POLL_INTERVAL)

    async def _get_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _poll(self):
        session = await self._get_session()
        try:
            async with session.get(self.ALL_PRICE_URL, timeout=5) as resp:
                if resp.status != 200:
                    logger.warning("[PricePoller] HTTP %s", resp.status)
                    return
                data = await resp.json()
        except asyncio.TimeoutError:
            logger.debug("[PricePoller] timeout")
            return
        except Exception as e:
            logger.debug("[PricePoller] fetch error: %s", e)
            return

        now_ms = int(time.time() * 1000)
        r = await get_redis_master()
        pipe = r.pipeline()
        total = written = 0
        for item in data:
            symbol = item.get("symbol", "")
            if not symbol.endswith("USDT"):
                continue
            total += 1
            try:
                price = float(item["price"])
            except (ValueError, TypeError):
                continue
            key = f"ticker:latest:binance:{symbol}"
            pipe.hset(key, mapping={
                "price": str(price),
                "event_time": str(now_ms),
                "exchange": "binance",
            })
            pipe.expire(key, 300)
            written += 1
        if written:
            await pipe.execute()
        elapsed = int((time.time() * 1000) - now_ms)
        logger.info("[PricePoller] wrote %d USDT symbols (%.0fms)", written, elapsed)


class MarketFetcherTask:
    """Background task to fetch and cache market metrics."""

    def __init__(self, interval_seconds: int = 300):
        self.interval_seconds = interval_seconds
        self.task = None
        self.running = False

    async def start(self):
        """Start the background task."""
        if self.running:
            logger.warning("Market fetcher already running")
            return

        self.running = True
        self.task = asyncio.create_task(self._run())
        logger.info("Market fetcher task started (interval: %ds)", self.interval_seconds)

    async def stop(self):
        """Stop the background task."""
        if not self.running:
            return

        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Market fetcher task stopped")

    async def _run(self):
        """Main loop to fetch market metrics periodically."""
        # Delay first fetch to avoid blocking startup
        await asyncio.sleep(5)
        await self._fetch_and_cache()

        while self.running:
            try:
                await asyncio.sleep(self.interval_seconds)
                if self.running:
                    await self._fetch_and_cache()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in market fetcher loop: %s", e, exc_info=True)
                await asyncio.sleep(60)  # Wait 1 min before retry

    async def _fetch_and_cache(self):
        """Fetch market metrics from Trino gold layer and update cache."""
        try:
            logger.info("Fetching market metrics from gold layer...")
            start_time = datetime.now()

            # Fetch in thread pool (blocking I/O)
            metrics, summary = await asyncio.to_thread(self._query_gold_layer)

            # Update cache
            market_service.update_market_cache(metrics, summary)

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(
                "✅ Fetched %d symbols in %.2fs (total_cap: $%.2fB, btc_dominance: %.1f%%)",
                len(metrics),
                elapsed,
                summary.get("total_market_cap", 0) / 1e9,
                summary.get("btc_dominance", 0)
            )

        except Exception as e:
            logger.error("Failed to fetch market metrics: %s", e, exc_info=True)

    def _query_gold_layer(self) -> tuple[List[Dict], Dict]:
        """Query Trino for market metrics from crypto_lakehouse tables."""
        conn = get_trino_connection()
        cursor = conn.cursor()

        try:
            # Query ticker data from crypto_lakehouse
            query = """
            SELECT
                symbol,
                close,
                h24_price_change_pct,
                h24_volume,
                h24_quote_volume
            FROM iceberg.crypto_lakehouse.coin_ticker
            WHERE symbol LIKE '%USDT'
            ORDER BY h24_quote_volume DESC
            LIMIT 500
            """

            cursor.execute(query)
            rows = cursor.fetchall()

            metrics = []
            for row in rows:
                metrics.append({
                    "symbol": row[0],
                    "price": float(row[1]) if row[1] else 0,
                    "change_24h_pct": float(row[2]) if row[2] else 0,
                    "volume_24h": float(row[3]) if row[3] else 0,
                    "market_cap": 0,  # Not available in ticker table
                    "rank": len(metrics) + 1,
                })

            # Calculate summary stats
            total_volume_24h = sum(m["volume_24h"] for m in metrics)
            btc_metrics = next((m for m in metrics if m["symbol"] == "BTCUSDT"), None)

            # Estimate market cap from volume (rough approximation)
            total_market_cap = total_volume_24h * 10 if total_volume_24h > 0 else 0
            btc_dominance = 40.0 if btc_metrics else 0  # Default estimate

            summary = {
                "total_symbols": len(metrics),
                "total_market_cap": total_market_cap,
                "total_volume_24h": total_volume_24h,
                "btc_dominance": btc_dominance,
                "btc_price": btc_metrics["price"] if btc_metrics else 0,
            }

            return metrics, summary

        except Exception as e:
            logger.error("Trino query failed: %s", e)
            # Return empty data on error
            return [], {
                "total_symbols": 0,
                "total_market_cap": 0,
                "total_volume_24h": 0,
                "btc_dominance": 0,
                "btc_price": 0,
            }
        finally:
            cursor.close()
            conn.close()


# Global instances
market_fetcher = MarketFetcherTask(interval_seconds=300)  # 5 minutes
binance_price_poller = BinancePricePoller()  # 500ms real-time poller
