"""
Gold Layer - News Aggregations
Calculate daily sentiment metrics per symbol
"""
import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, count, avg, sum as _sum, collect_list, array_distinct,
    current_timestamp, to_date, desc, struct, when, size
)
from pyspark.sql.window import Window

logger = logging.getLogger(__name__)


class GoldNewsSentiment:
    """Calculate news sentiment aggregations"""

    def __init__(self, spark: SparkSession):
        self.spark = spark
        self.silver_table = "iceberg.crypto_lakehouse.silver_news_enriched"
        self.gold_table = "iceberg.crypto_lakehouse.gold_news_sentiment_daily"

    def create_table(self):
        """Create Gold news_sentiment_daily table"""
        create_sql = """
        CREATE TABLE IF NOT EXISTS iceberg.crypto_lakehouse.gold_news_sentiment_daily (
            symbol STRING NOT NULL,
            date DATE NOT NULL,
            article_count INT NOT NULL,
            avg_sentiment DOUBLE,
            sentiment_positive INT,
            sentiment_neutral INT,
            sentiment_negative INT,
            avg_impact_score DOUBLE,
            top_sources ARRAY<STRING>,
            trending_tags ARRAY<STRING>,
            top_headlines ARRAY<STRUCT<title:STRING, sentiment:DOUBLE, url:STRING>>
        ) USING iceberg
        PARTITIONED BY (date)
        TBLPROPERTIES (
            'write.format.default' = 'parquet',
            'write.parquet.compression-codec' = 'snappy'
        )
        """
        self.spark.sql(create_sql)
        logger.info("Created gold.news_sentiment_daily table")

    def calculate(self, date: str = None):
        """
        Calculate daily sentiment metrics per symbol

        Args:
            date: Date to process (YYYY-MM-DD), defaults to today
        """
        from pyspark.sql.functions import explode, lit

        if not date:
            from datetime import datetime
            date = datetime.now().strftime("%Y-%m-%d")

        # Read Silver news
        silver_df = self.spark.table(self.silver_table) \
            .filter(col("_partition_date") == date)

        # Explode symbols array (one row per symbol)
        exploded_df = silver_df.select(
            explode(col("symbols")).alias("symbol"),
            col("source"),
            col("title"),
            col("url"),
            col("sentiment_score"),
            col("sentiment_label"),
            col("impact_score"),
            col("_partition_date")
        )

        # Calculate sentiment distribution
        sentiment_stats = exploded_df.groupBy("symbol").agg(
            count("*").alias("article_count"),
            avg("sentiment_score").alias("avg_sentiment"),
            _sum(when(col("sentiment_score") > 0.05, 1).otherwise(0)).alias("sentiment_positive"),
            _sum(when((col("sentiment_score") >= -0.05) & (col("sentiment_score") <= 0.05), 1).otherwise(0)).alias("sentiment_neutral"),
            _sum(when(col("sentiment_score") < -0.05, 1).otherwise(0)).alias("sentiment_negative"),
            avg("impact_score").alias("avg_impact_score")
        )

        # Get top sources per symbol
        source_window = Window.partitionBy("symbol").orderBy(desc("source_count"))
        top_sources_df = exploded_df.groupBy("symbol", "source").agg(
            count("*").alias("source_count")
        ).withColumn("rank", expr("row_number() OVER (PARTITION BY symbol ORDER BY source_count DESC)")) \
         .filter(col("rank") <= 5) \
         .groupBy("symbol").agg(
             collect_list("source").alias("top_sources")
         )

        # Get top headlines per symbol (by impact score)
        headline_window = Window.partitionBy("symbol").orderBy(desc("impact_score"))
        top_headlines_df = exploded_df.withColumn(
            "rank", expr("row_number() OVER (PARTITION BY symbol ORDER BY impact_score DESC)")
        ).filter(col("rank") <= 3) \
         .groupBy("symbol").agg(
             collect_list(
                 struct(
                     col("title"),
                     col("sentiment_score").alias("sentiment"),
                     col("url")
                 )
             ).alias("top_headlines")
         )

        # Combine all metrics
        result = sentiment_stats \
            .join(top_sources_df, "symbol", "left") \
            .join(top_headlines_df, "symbol", "left") \
            .withColumn("date", lit(date).cast("date")) \
            .withColumn("trending_tags", array_distinct(collect_list(lit("")))) \
            .select(
                "symbol",
                "date",
                "article_count",
                "avg_sentiment",
                "sentiment_positive",
                "sentiment_neutral",
                "sentiment_negative",
                "avg_impact_score",
                "top_sources",
                "trending_tags",
                "top_headlines"
            )

        # Write to Gold
        result.write \
            .format("iceberg") \
            .mode("overwrite") \
            .option("overwrite-mode", "dynamic") \
            .saveAsTable(self.gold_table)

        count = result.count()
        logger.info(f"Calculated sentiment for {count} symbols on {date}")
        return count


class GoldNewsImpact:
    """Calculate market impact from news"""

    def __init__(self, spark: SparkSession):
        self.spark = spark
        self.news_table = "iceberg.crypto_lakehouse.silver_news_enriched"
        self.ticker_table = "iceberg.crypto_lakehouse.silver_ticker_unified"
        self.gold_table = "iceberg.crypto_lakehouse.gold_news_market_impact"

    def create_table(self):
        """Create Gold news_market_impact table"""
        create_sql = """
        CREATE TABLE IF NOT EXISTS iceberg.crypto_lakehouse.gold_news_market_impact (
            symbol STRING NOT NULL,
            news_published_at BIGINT NOT NULL,
            news_title STRING,
            news_sentiment DOUBLE,
            price_before DOUBLE,
            price_after_1h DOUBLE,
            price_after_24h DOUBLE,
            price_change_1h_pct DOUBLE,
            price_change_24h_pct DOUBLE,
            volume_before DOUBLE,
            volume_after_1h DOUBLE,
            volume_change_pct DOUBLE,
            impact_correlation DOUBLE,
            _partition_date DATE NOT NULL
        ) USING iceberg
        PARTITIONED BY (_partition_date)
        """
        self.spark.sql(create_sql)
        logger.info("Created gold.news_market_impact table")

    def calculate(self, date: str = None):
        """
        Calculate correlation between news and price movement

        Args:
            date: Date to process (YYYY-MM-DD)
        """
        from pyspark.sql.functions import explode, lit, expr

        if not date:
            from datetime import datetime
            date = datetime.now().strftime("%Y-%m-%d")

        # Read news
        news_df = self.spark.table(self.news_table) \
            .filter(col("_partition_date") == date) \
            .select(
                explode(col("symbols")).alias("symbol"),
                col("published_at"),
                col("title"),
                col("sentiment_score"),
                col("impact_score")
            )

        # Read ticker data
        ticker_df = self.spark.table(self.ticker_table) \
            .filter(col("_partition_date") == date) \
            .select(
                col("symbol"),
                col("event_time"),
                col("price_mid").alias("price"),
                col("volume_total").alias("volume")
            )

        # Join news with price before/after
        # Price before: within 1h before news
        # Price after 1h: 1h after news
        # Price after 24h: 24h after news

        joined_df = news_df.alias("n").join(
            ticker_df.alias("t_before"),
            (col("n.symbol") == col("t_before.symbol")) &
            (col("t_before.event_time") >= col("n.published_at") - 3600000) &
            (col("t_before.event_time") < col("n.published_at")),
            "left"
        ).join(
            ticker_df.alias("t_after_1h"),
            (col("n.symbol") == col("t_after_1h.symbol")) &
            (col("t_after_1h.event_time") >= col("n.published_at")) &
            (col("t_after_1h.event_time") < col("n.published_at") + 3600000),
            "left"
        ).join(
            ticker_df.alias("t_after_24h"),
            (col("n.symbol") == col("t_after_24h.symbol")) &
            (col("t_after_24h.event_time") >= col("n.published_at")) &
            (col("t_after_24h.event_time") < col("n.published_at") + 86400000),
            "left"
        )

        # Calculate impact metrics
        result = joined_df.select(
            col("n.symbol"),
            col("n.published_at").alias("news_published_at"),
            col("n.title").alias("news_title"),
            col("n.sentiment_score").alias("news_sentiment"),
            avg("t_before.price").alias("price_before"),
            avg("t_after_1h.price").alias("price_after_1h"),
            avg("t_after_24h.price").alias("price_after_24h"),
            avg("t_before.volume").alias("volume_before"),
            avg("t_after_1h.volume").alias("volume_after_1h")
        ).groupBy(
            "symbol", "news_published_at", "news_title", "news_sentiment"
        ).agg(
            avg("price_before").alias("price_before"),
            avg("price_after_1h").alias("price_after_1h"),
            avg("price_after_24h").alias("price_after_24h"),
            avg("volume_before").alias("volume_before"),
            avg("volume_after_1h").alias("volume_after_1h")
        ).withColumn(
            "price_change_1h_pct",
            when(col("price_before") > 0,
                 ((col("price_after_1h") - col("price_before")) / col("price_before")) * 100)
            .otherwise(0)
        ).withColumn(
            "price_change_24h_pct",
            when(col("price_before") > 0,
                 ((col("price_after_24h") - col("price_before")) / col("price_before")) * 100)
            .otherwise(0)
        ).withColumn(
            "volume_change_pct",
            when(col("volume_before") > 0,
                 ((col("volume_after_1h") - col("volume_before")) / col("volume_before")) * 100)
            .otherwise(0)
        ).withColumn(
            "impact_correlation",
            # Correlation: positive sentiment → positive price change
            when(
                (col("news_sentiment") > 0) & (col("price_change_1h_pct") > 0),
                col("news_sentiment") * col("price_change_1h_pct") / 100
            ).when(
                (col("news_sentiment") < 0) & (col("price_change_1h_pct") < 0),
                abs(col("news_sentiment")) * abs(col("price_change_1h_pct")) / 100
            ).otherwise(0)
        ).withColumn("_partition_date", lit(date).cast("date"))

        # Write to Gold
        result.writeTo(self.gold_table).append()

        count = result.count()
        logger.info(f"Calculated news impact for {count} events on {date}")
        return count
