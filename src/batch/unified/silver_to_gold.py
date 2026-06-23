"""
Unified Silver → Gold Aggregation
Consolidates all Gold market metrics into single job
Reduces I/O from 5 reads → 1 read (80% reduction)
"""
import os
import sys
from pathlib import Path
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, sum as _sum, avg, max as _max, min as _min, count,
    current_timestamp, to_date, desc, asc, when, expr, lit,
    stddev, collect_list, struct, row_number, abs as _abs, lag
)
from pyspark.sql.window import Window
import logging
from datetime import datetime

PROJECT_DIR = Path(os.environ.get("CRYPTO_PROJECT_DIR", "/app"))
sys.path.insert(0, str(PROJECT_DIR / "src"))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def create_spark_session():
    """Create Spark session with Iceberg config"""
    return SparkSession.builder \
        .appName("Unified_Silver_to_Gold") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
        .config("spark.sql.catalog.iceberg_catalog", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.iceberg_catalog.type", "hadoop") \
        .config("spark.sql.catalog.iceberg_catalog.warehouse", "s3a://cryptoprice/warehouse") \
        .config("spark.sql.catalog.iceberg_catalog.io-impl", "org.apache.iceberg.aws.s3.S3FileIO") \
        .config("spark.hadoop.fs.s3a.endpoint", os.getenv("MINIO_ENDPOINT", "http://minio:9000")
        .config("spark.hadoop.fs.s3a.access.key", os.getenv("MINIO_ACCESS_KEY", "")
        .config("spark.hadoop.fs.s3a.secret.key", os.getenv("MINIO_SECRET_KEY", "")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider") \
        .config("spark.sql.catalog.iceberg_catalog.client.region", "us-east-1") \
        .config("spark.sql.catalog.iceberg_catalog.s3.endpoint", os.getenv("MINIO_ENDPOINT", "http://minio:9000")
        .config("spark.sql.catalog.iceberg_catalog.s3.access-key-id", os.getenv("MINIO_ACCESS_KEY", "")
        .config("spark.sql.catalog.iceberg_catalog.s3.secret-access-key", os.getenv("MINIO_SECRET_KEY", "")
        .getOrCreate()


def create_gold_tables(spark: SparkSession):
    """Create all Gold tables"""

    # Market overview
    spark.sql("""
        CREATE TABLE IF NOT EXISTS iceberg.crypto_lakehouse.market_overview (
            snapshot_time TIMESTAMP,
            total_symbols INT,
            total_volume_24h DOUBLE,
            avg_spread_pct DOUBLE,
            top_10_gainers ARRAY<STRUCT<symbol:STRING, change_pct:DOUBLE, price:DOUBLE>>,
            top_10_losers ARRAY<STRUCT<symbol:STRING, change_pct:DOUBLE, price:DOUBLE>>,
            market_cap_total DOUBLE,
            _partition_date DATE
        ) USING iceberg
        PARTITIONED BY (_partition_date)
    """)

    # Market dominance
    spark.sql("""
        CREATE TABLE IF NOT EXISTS iceberg.crypto_lakehouse.market_dominance (
            snapshot_time TIMESTAMP NOT NULL,
            btc_dominance_pct DOUBLE,
            eth_dominance_pct DOUBLE,
            stablecoin_volume_pct DOUBLE,
            altcoin_volume_pct DOUBLE,
            total_market_cap DOUBLE,
            total_volume_24h DOUBLE,
            active_symbols INT,
            _partition_date DATE NOT NULL
        ) USING iceberg
        PARTITIONED BY (_partition_date)
    """)

    # Volatility ranking
    spark.sql("""
        CREATE TABLE IF NOT EXISTS iceberg.crypto_lakehouse.volatility_ranking (
            symbol STRING NOT NULL,
            snapshot_time TIMESTAMP NOT NULL,
            volatility_1h DOUBLE,
            volatility_24h DOUBLE,
            volatility_7d DOUBLE,
            rank_by_volatility INT,
            price_range_pct_24h DOUBLE,
            _partition_date DATE NOT NULL
        ) USING iceberg
        PARTITIONED BY (_partition_date)
    """)

    # Movers ranking
    spark.sql("""
        CREATE TABLE IF NOT EXISTS iceberg.crypto_lakehouse.movers_ranking (
            symbol STRING NOT NULL,
            rank INT NOT NULL,
            category STRING NOT NULL,
            timeframe STRING NOT NULL,
            change_pct DOUBLE NOT NULL,
            current_price DOUBLE,
            volume_24h DOUBLE,
            volume_change_pct DOUBLE,
            snapshot_time TIMESTAMP NOT NULL,
            _partition_date DATE NOT NULL
        ) USING iceberg
        PARTITIONED BY (_partition_date, timeframe)
    """)

    # Sector performance
    spark.sql("""
        CREATE TABLE IF NOT EXISTS iceberg.crypto_lakehouse.sector_performance (
            sector STRING,
            snapshot_time TIMESTAMP,
            avg_change_pct DOUBLE,
            total_volume DOUBLE,
            symbol_count INT,
            top_symbol STRING,
            top_symbol_change_pct DOUBLE,
            _partition_date DATE
        ) USING iceberg
        PARTITIONED BY (_partition_date)
    """)

    # Coin ticker (for API)
    spark.sql("""
        CREATE TABLE IF NOT EXISTS iceberg.crypto_lakehouse.coin_ticker (
            symbol STRING,
            close DOUBLE,
            h24_price_change_pct DOUBLE,
            h24_volume DOUBLE,
            h24_quote_volume DOUBLE,
            market_cap DOUBLE,
            rank INT,
            last_updated TIMESTAMP
        ) USING iceberg
    """)

    logger.info("Created all Gold tables")


def calculate_all_metrics(ticker_df):
    """
    Calculate ALL Gold metrics from single Silver ticker read
    Returns dict of DataFrames for each metric
    """
    logger.info("Calculating all Gold metrics from cached ticker data...")

    # Cache ticker data in memory (read ONCE, use multiple times)
    ticker_df.cache()

    now_ms = int(datetime.now().timestamp() * 1000)
    time_1h_ago = now_ms - (1 * 60 * 60 * 1000)
    time_24h_ago = now_ms - (24 * 60 * 60 * 1000)
    time_7d_ago = now_ms - (7 * 24 * 60 * 60 * 1000)

    results = {}

    # ========== 1. Market Overview ==========
    logger.info("  [1/6] Calculating market overview...")

    # Calculate 24h change
    window_24h = Window.partitionBy("symbol").orderBy("event_time").rangeBetween(-86400000, 0)
    metrics = ticker_df.withColumn(
        "price_24h_ago",
        lag("price_mid", 1).over(window_24h)
    ).withColumn(
        "change_pct_24h",
        when(col("price_24h_ago").isNotNull() & (col("price_24h_ago") > 0),
             ((col("price_mid") - col("price_24h_ago")) / col("price_24h_ago")) * 100)
        .otherwise(0)
    )

    # Get latest snapshot
    latest_window = Window.partitionBy("symbol").orderBy(desc("event_time"))
    latest_metrics = metrics.withColumn("row_num", row_number().over(latest_window)) \
                           .filter(col("row_num") == 1) \
                           .drop("row_num")

    # Top 10 gainers
    top_gainers = latest_metrics.orderBy(desc("change_pct_24h")).limit(10) \
                                .select(
                                    struct(
                                        col("symbol"),
                                        col("change_pct_24h").alias("change_pct"),
                                        col("price_mid").alias("price")
                                    ).alias("gainer")
                                ) \
                                .agg(collect_list("gainer").alias("top_10_gainers"))

    # Top 10 losers
    top_losers = latest_metrics.orderBy(asc("change_pct_24h")).limit(10) \
                               .select(
                                   struct(
                                       col("symbol"),
                                       col("change_pct_24h").alias("change_pct"),
                                       col("price_mid").alias("price")
                                   ).alias("loser")
                               ) \
                               .agg(collect_list("loser").alias("top_10_losers"))

    # Aggregate metrics
    overview = latest_metrics.agg(
        count("symbol").alias("total_symbols"),
        _sum("volume_total").alias("total_volume_24h"),
        avg("spread_pct").alias("avg_spread_pct"),
        _sum(col("price_mid") * col("volume_total")).alias("market_cap_total")
    )

    # Combine
    results['market_overview'] = overview.crossJoin(top_gainers).crossJoin(top_losers) \
                    .withColumn("snapshot_time", current_timestamp()) \
                    .withColumn("_partition_date", to_date(current_timestamp()))

    # ========== 2. Market Dominance ==========
    logger.info("  [2/6] Calculating market dominance...")

    latest_df = ticker_df.withColumn("rank", row_number().over(latest_window)) \
                         .filter(col("rank") == 1) \
                         .drop("rank")

    market_df = latest_df.withColumn(
        "market_cap",
        col("price_mid") * col("volume_total") * 10
    )

    total_market_cap = market_df.agg(_sum("market_cap")).collect()[0][0] or 1
    total_volume = market_df.agg(_sum("volume_total")).collect()[0][0] or 1

    btc_cap = market_df.filter(col("symbol") == "BTCUSDT").agg(_sum("market_cap")).collect()[0][0] or 0
    eth_cap = market_df.filter(col("symbol") == "ETHUSDT").agg(_sum("market_cap")).collect()[0][0] or 0

    stablecoins = ["USDCUSDT", "BUSDUSDT", "TUSDUSDT", "DAIUSDT"]
    stablecoin_vol = market_df.filter(col("symbol").isin(stablecoins)).agg(_sum("volume_total")).collect()[0][0] or 0

    major_coins = ["BTCUSDT", "ETHUSDT"] + stablecoins
    altcoin_vol = market_df.filter(~col("symbol").isin(major_coins)).agg(_sum("volume_total")).collect()[0][0] or 0

    active_symbols = market_df.count()

    dominance_data = [{
        "snapshot_time": datetime.now(),
        "btc_dominance_pct": round((btc_cap / total_market_cap) * 100, 2),
        "eth_dominance_pct": round((eth_cap / total_market_cap) * 100, 2),
        "stablecoin_volume_pct": round((stablecoin_vol / total_volume) * 100, 2),
        "altcoin_volume_pct": round((altcoin_vol / total_volume) * 100, 2),
        "total_market_cap": round(total_market_cap, 2),
        "total_volume_24h": round(total_volume, 2),
        "active_symbols": active_symbols,
        "_partition_date": datetime.now().date()
    }]

    results['market_dominance'] = ticker_df.sparkSession.createDataFrame(dominance_data)

    # ========== 3. Volatility Ranking ==========
    logger.info("  [3/6] Calculating volatility ranking...")

    vol_1h = ticker_df.filter(col("event_time") >= time_1h_ago) \
                     .groupBy("symbol").agg(stddev("price_mid").alias("volatility_1h"))

    vol_24h = ticker_df.filter(col("event_time") >= time_24h_ago) \
                      .groupBy("symbol").agg(
                          stddev("price_mid").alias("volatility_24h"),
                          _max("price_mid").alias("high_24h"),
                          _min("price_mid").alias("low_24h")
                      )

    vol_7d = ticker_df.filter(col("event_time") >= time_7d_ago) \
                     .groupBy("symbol").agg(stddev("price_mid").alias("volatility_7d"))

    volatility_result = vol_1h.join(vol_24h, "symbol", "left") \
                  .join(vol_7d, "symbol", "left") \
                  .withColumn(
                      "price_range_pct_24h",
                      when(col("low_24h") > 0,
                           ((col("high_24h") - col("low_24h")) / col("low_24h")) * 100)
                      .otherwise(0)
                  ) \
                  .withColumn("rank_by_volatility", row_number().over(Window.orderBy(desc("volatility_24h")))) \
                  .withColumn("snapshot_time", current_timestamp()) \
                  .withColumn("_partition_date", to_date(current_timestamp())) \
                  .select(
                      "symbol", "snapshot_time", "volatility_1h", "volatility_24h",
                      "volatility_7d", "rank_by_volatility", "price_range_pct_24h", "_partition_date"
                  )

    results['volatility_ranking'] = volatility_result

    # ========== 4. Movers Ranking ==========
    logger.info("  [4/6] Calculating movers ranking...")

    timeframes = {
        "1h": time_1h_ago,
        "24h": time_24h_ago,
        "7d": time_7d_ago
    }

    all_movers = []

    for tf_name, tf_start in timeframes.items():
        window_start = Window.partitionBy("symbol").orderBy(asc("event_time"))
        window_end = Window.partitionBy("symbol").orderBy(desc("event_time"))

        df_period = ticker_df.filter(col("event_time") >= tf_start)

        first_price = df_period.withColumn("rank", row_number().over(window_start)) \
                              .filter(col("rank") == 1) \
                              .select(
                                  col("symbol"),
                                  col("price_mid").alias("price_start"),
                                  col("volume_total").alias("volume_start")
                              )

        last_price = df_period.withColumn("rank", row_number().over(window_end)) \
                             .filter(col("rank") == 1) \
                             .select(
                                 col("symbol"),
                                 col("price_mid").alias("price_end"),
                                 col("volume_total").alias("volume_end")
                             )

        changes = first_price.join(last_price, "symbol") \
                            .withColumn(
                                "change_pct",
                                when(col("price_start") > 0,
                                     ((col("price_end") - col("price_start")) / col("price_start")) * 100)
                                .otherwise(0)
                            ).withColumn(
                                "volume_change_pct",
                                when(col("volume_start") > 0,
                                     ((col("volume_end") - col("volume_start")) / col("volume_start")) * 100)
                                .otherwise(0)
                            )

        gainers = changes.filter(col("change_pct") > 0) \
                        .orderBy(desc("change_pct")) \
                        .limit(20) \
                        .withColumn("rank", row_number().over(Window.orderBy(desc("change_pct")))) \
                        .withColumn("category", lit("gainer")) \
                        .withColumn("timeframe", lit(tf_name))

        losers = changes.filter(col("change_pct") < 0) \
                       .orderBy(asc("change_pct")) \
                       .limit(20) \
                       .withColumn("rank", row_number().over(Window.orderBy(asc("change_pct")))) \
                       .withColumn("category", lit("loser")) \
                       .withColumn("timeframe", lit(tf_name))

        movers = gainers.union(losers).select(
            "symbol", "rank", "category", "timeframe", "change_pct",
            col("price_end").alias("current_price"),
            col("volume_end").alias("volume_24h"),
            "volume_change_pct"
        )

        all_movers.append(movers)

    final_movers = all_movers[0]
    for df in all_movers[1:]:
        final_movers = final_movers.union(df)

    results['movers_ranking'] = final_movers.withColumn("snapshot_time", current_timestamp()) \
                              .withColumn("_partition_date", to_date(current_timestamp()))

    # ========== 5. Sector Performance ==========
    logger.info("  [5/6] Calculating sector performance...")

    categorized = latest_metrics.withColumn(
        "sector",
        when(col("volume_total") > 1000000, "Large Cap")
        .when(col("volume_total") > 100000, "Mid Cap")
        .otherwise("Small Cap")
    )

    sector_stats = categorized.groupBy("sector").agg(
        avg("change_pct_24h").alias("avg_change_pct"),
        _sum("volume_total").alias("total_volume"),
        count("symbol").alias("symbol_count")
    )

    top_symbols = categorized.withColumn("rank", row_number().over(Window.partitionBy("sector").orderBy(desc("change_pct_24h")))) \
                           .filter(col("rank") == 1) \
                           .select(
                               col("sector"),
                               col("symbol").alias("top_symbol"),
                               col("change_pct_24h").alias("top_symbol_change_pct")
                           )

    results['sector_performance'] = sector_stats.join(top_symbols, "sector") \
                        .withColumn("snapshot_time", current_timestamp()) \
                        .withColumn("_partition_date", to_date(current_timestamp()))

    # ========== 6. Coin Ticker (API Support) ==========
    logger.info("  [6/6] Populating coin_ticker...")

    price_24h_df = ticker_df.filter(
        (col("event_time") >= time_24h_ago - 300000) &
        (col("event_time") <= time_24h_ago + 300000)
    ).groupBy("symbol").agg(avg("price_mid").alias("price_24h_ago"))

    volume_24h_df = ticker_df.filter(col("event_time") >= time_24h_ago) \
                            .groupBy("symbol").agg(_sum("volume_total").alias("h24_volume"))

    coin_ticker = latest_df.select(col("symbol"), col("price_mid").alias("close")) \
                 .join(price_24h_df, "symbol", "left") \
                 .join(volume_24h_df, "symbol", "left") \
                 .withColumn(
                     "h24_price_change_pct",
                     when((col("price_24h_ago").isNotNull()) & (col("price_24h_ago") > 0),
                          ((col("close") - col("price_24h_ago")) / col("price_24h_ago")) * 100)
                     .otherwise(0)
                 ) \
                 .withColumn("h24_quote_volume", col("close") * col("h24_volume")) \
                 .withColumn("market_cap", col("h24_quote_volume") * 10) \
                 .withColumn("rank", row_number().over(Window.orderBy(desc("h24_quote_volume")))) \
                 .withColumn("last_updated", current_timestamp()) \
                 .select(
                     "symbol", "close", "h24_price_change_pct", "h24_volume",
                     "h24_quote_volume", "market_cap", "rank", "last_updated"
                 ).filter(col("symbol").like("%USDT"))

    results['coin_ticker'] = coin_ticker

    # Unpersist cache
    ticker_df.unpersist()

    logger.info("All metrics calculated successfully")
    return results


def main():
    """Main aggregation pipeline"""
    logger.info("=" * 80)
    logger.info("Starting Unified Silver → Gold Aggregation")
    logger.info("=" * 80)

    spark = create_spark_session()

    try:
        # Create Gold tables
        create_gold_tables(spark)

        # Read Silver ticker ONCE
        logger.info("Reading silver.ticker_unified...")
        ticker_df = spark.table("iceberg.crypto_lakehouse.ticker_unified")

        # Calculate ALL metrics from single read
        metrics = calculate_all_metrics(ticker_df)

        # Write all Gold tables
        logger.info("Writing Gold tables...")

        logger.info("  Writing market_overview...")
        metrics['market_overview'].write \
            .format("iceberg") \
            .mode("append") \
            .saveAsTable("iceberg.crypto_lakehouse.market_overview")

        logger.info("  Writing market_dominance...")
        metrics['market_dominance'].writeTo("iceberg.crypto_lakehouse.market_dominance").append()

        logger.info("  Writing volatility_ranking...")
        metrics['volatility_ranking'].write \
            .format("iceberg") \
            .mode("overwrite") \
            .option("overwrite-mode", "dynamic") \
            .saveAsTable("iceberg.crypto_lakehouse.volatility_ranking")

        logger.info("  Writing movers_ranking...")
        metrics['movers_ranking'].write \
            .format("iceberg") \
            .mode("overwrite") \
            .option("overwrite-mode", "dynamic") \
            .saveAsTable("iceberg.crypto_lakehouse.movers_ranking")

        logger.info("  Writing sector_performance...")
        metrics['sector_performance'].write \
            .format("iceberg") \
            .mode("append") \
            .saveAsTable("iceberg.crypto_lakehouse.sector_performance")

        logger.info("  Writing coin_ticker...")
        metrics['coin_ticker'].write \
            .format("iceberg") \
            .mode("overwrite") \
            .saveAsTable("iceberg.crypto_lakehouse.coin_ticker")

        # Summary
        logger.info("=" * 80)
        logger.info("Unified Silver → Gold Aggregation completed successfully")
        logger.info(f"  Market overview: {metrics['market_overview'].count()} rows")
        logger.info(f"  Market dominance: {metrics['market_dominance'].count()} rows")
        logger.info(f"  Volatility ranking: {metrics['volatility_ranking'].count()} symbols")
        logger.info(f"  Movers ranking: {metrics['movers_ranking'].count()} entries")
        logger.info(f"  Sector performance: {metrics['sector_performance'].count()} sectors")
        logger.info(f"  Coin ticker: {metrics['coin_ticker'].count()} symbols")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Aggregation failed: {e}", exc_info=True)
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    main()


