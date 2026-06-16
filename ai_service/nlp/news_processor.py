"""Background news processing worker for FinBERT sentiment analysis.

Processes news articles from the PostgreSQL news cache and stores
FinBERT sentiment results in the news_sentiment_cache table.

Designed to run as a standalone process or background task.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import signal
import sys
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ai_service.nlp.news_processor")

# Processing interval in seconds
DEFAULT_PROCESS_INTERVAL = int(os.environ.get("FINBERT_PROCESS_INTERVAL", "300"))
DEFAULT_BATCH_SIZE = int(os.environ.get("FINBERT_BATCH_SIZE", "32"))


class NewsProcessor:
    """Background worker that processes news articles with FinBERT.

    Reads unprocessed articles from the news database, runs FinBERT
    sentiment analysis, entity extraction, and event classification,
    then stores results in the news_sentiment_cache table.
    """

    def __init__(
        self,
        process_interval: int = DEFAULT_PROCESS_INTERVAL,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ):
        self.process_interval = process_interval
        self.batch_size = batch_size
        self._running = False
        self._analyzer = None
        self._processed_count = 0

    def _get_analyzer(self):
        """Lazy-load FinBERT analyzer."""
        if self._analyzer is None:
            from ai_service.nlp.finbert import FinBERTAnalyzer
            self._analyzer = FinBERTAnalyzer(
                device=os.environ.get("FINBERT_DEVICE", "auto"),
            )
            self._analyzer.load()
            logger.info("FinBERT analyzer initialized on %s.", self._analyzer.device)
        return self._analyzer

    async def run(self) -> None:
        """Main processing loop."""
        self._running = True
        logger.info(
            "FinBERT news processor started (interval=%ds, batch=%d).",
            self.process_interval, self.batch_size,
        )

        while self._running:
            try:
                processed = await self._process_batch()
                self._processed_count += processed
                if processed > 0:
                    logger.info(
                        "Processed %d articles (total: %d).",
                        processed, self._processed_count,
                    )
            except Exception as exc:
                logger.error("Processing cycle failed: %s", exc, exc_info=True)

            await asyncio.sleep(self.process_interval)

    async def _process_batch(self) -> int:
        """Process one batch of unprocessed articles."""
        try:
            import asyncpg
        except ImportError:
            logger.error("asyncpg not installed. Required for news processing.")
            return 0

        db_url = _build_db_url()
        if not db_url:
            logger.warning("Database URL not configured. Skipping.")
            return 0

        conn = await asyncpg.connect(db_url)
        try:
            # Find articles not yet processed by FinBERT
            rows = await conn.fetch(
                """
                SELECT n.title, n.source, n.url, n.published_at
                FROM news_articles n
                LEFT JOIN news_sentiment_cache c ON c.article_hash = encode(
                    digest(n.title || COALESCE(n.url, ''), 'sha256'), 'hex'
                )
                WHERE c.id IS NULL
                ORDER BY n.published_at DESC NULLS LAST
                LIMIT $1
                """,
                self.batch_size,
            )

            if not rows:
                return 0

            # Run FinBERT analysis
            analyzer = self._get_analyzer()
            from ai_service.nlp.entity_extractor import (
                extract_entities,
                classify_event,
                extract_affected_assets,
                estimate_market_relevance,
            )

            titles = [row["title"] for row in rows]
            sentiments = analyzer.analyze_batch(titles)

            # Store results
            for row, sentiment in zip(rows, sentiments):
                title = row["title"]
                article_hash = hashlib.sha256(
                    (title + (row["url"] or "")).encode()
                ).hexdigest()

                entities = extract_entities(title)
                event_category = classify_event(title)
                affected = extract_affected_assets(title)
                relevance = estimate_market_relevance(title)
                entity_names = [e.text for e in entities]

                await conn.execute(
                    """
                    INSERT INTO news_sentiment_cache (
                        article_hash, title, source, url,
                        sentiment_score, sentiment_confidence, sentiment_label,
                        detected_entities, event_category, affected_assets,
                        market_relevance, analyzer, article_published_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                    ON CONFLICT (article_hash) DO NOTHING
                    """,
                    article_hash,
                    title[:1000],
                    row.get("source"),
                    row.get("url"),
                    sentiment.score,
                    sentiment.confidence,
                    sentiment.label,
                    entity_names,
                    event_category,
                    affected,
                    relevance,
                    "finbert",
                    row.get("published_at"),
                )

            return len(rows)

        finally:
            await conn.close()

    def stop(self) -> None:
        """Signal the processor to stop."""
        self._running = False
        logger.info("FinBERT news processor stopping.")


def _build_db_url() -> Optional[str]:
    """Build PostgreSQL connection URL from environment variables."""
    user = os.environ.get("POSTGRES_USER", "iceberg")
    password = os.environ.get("POSTGRES_PASSWORD", "")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_LMVIEW_DB", "iceberg_catalog")

    if not password:
        return None

    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


async def main() -> None:
    """Entry point for the standalone FinBERT worker process."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    processor = NewsProcessor()

    # Handle graceful shutdown
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, processor.stop)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            pass

    await processor.run()


if __name__ == "__main__":
    asyncio.run(main())
