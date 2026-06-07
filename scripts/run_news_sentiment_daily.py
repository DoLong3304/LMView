import asyncio
import json
import time
import urllib.request

import asyncpg

TRINO_URL = "http://localhost:8083/v1/statement"
HEADERS = {
    "X-Trino-User": "news-sentiment-test",
    "X-Trino-Catalog": "iceberg",
    "X-Trino-Schema": "crypto_lakehouse",
}


def run_query(sql: str):
    req = urllib.request.Request(TRINO_URL, data=sql.encode("utf-8"), headers=HEADERS)
    with urllib.request.urlopen(req) as resp:
        payload = json.load(resp)
    next_uri = payload.get("nextUri")
    while next_uri:
        with urllib.request.urlopen(next_uri) as resp:
            payload = json.load(resp)
        next_uri = payload.get("nextUri")
        time.sleep(0.05)
    return payload.get("data", [])


async def main():
    conn = await asyncpg.connect(
        host="localhost",
        database="iceberg_catalog",
        user="iceberg",
        password="iceberg123",
    )
    rows = await conn.fetch(
        """
        SELECT
            date_trunc('day', published_at) AS date,
            unnest(symbols_mentioned) AS symbol,
            AVG(coalesce(sentiment_score, 0)) AS avg_sentiment,
            COUNT(*) AS article_count,
            SUM(CASE WHEN sentiment_label = 'bullish' THEN 1 ELSE 0 END) AS bullish_count,
            SUM(CASE WHEN sentiment_label = 'bearish' THEN 1 ELSE 0 END) AS bearish_count
        FROM news_articles
        WHERE symbols_mentioned IS NOT NULL
          AND array_length(symbols_mentioned, 1) > 0
          AND published_at >= NOW() - INTERVAL '7 days'
        GROUP BY 1, 2
        """
    )
    await conn.close()

    run_query(
        """
        CREATE TABLE IF NOT EXISTS gold_news_sentiment_daily (
            date TIMESTAMP(6) WITH TIME ZONE,
            symbol VARCHAR,
            avg_sentiment DOUBLE,
            article_count BIGINT,
            bullish_count BIGINT,
            bearish_count BIGINT,
            _partition_date DATE
        ) WITH (format='PARQUET', partitioning=ARRAY['_partition_date'])
        """
    )
    run_query("DELETE FROM gold_news_sentiment_daily WHERE _partition_date >= current_date - INTERVAL '7' day")

    for row in rows:
        sql = f"""
        INSERT INTO gold_news_sentiment_daily
        VALUES (
            TIMESTAMP '{row['date'].strftime('%Y-%m-%d %H:%M:%S')}' AT TIME ZONE 'UTC',
            '{row['symbol']}',
            {float(row['avg_sentiment'] or 0)},
            {int(row['article_count'] or 0)},
            {int(row['bullish_count'] or 0)},
            {int(row['bearish_count'] or 0)},
            DATE '{row['date'].date().isoformat()}'
        )
        """
        run_query(sql)
    print(f"wrote {len(rows)} rows")


if __name__ == "__main__":
    asyncio.run(main())
