"""
Gold Layer - Advanced Market Metrics
Calculate comprehensive market indicators for Overview tab
"""
import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, sum as _sum, avg, max as _max, min as _min, count,
    current_timestamp, to_date, desc, asc, when, expr, lit,
    stddev, lag, collect_list, struct, row_number, abs as _abs
)
from pyspark.sql.window import Window

logger = logging.getLogger(__name__)


class GoldMarketDominance:
    """Calculate market dominance metrics"""

    def __init__(self, spark: SparkSession):
        self.spark = spark
        self.ticker_table = "iceberg.crypto_lakehouse.silver_ticker_unified"
        self.gold_table = "iceberg.crypto_lakehouse.market_dominance"

    def create_table(self):
        """Create Gold market_dominance table"""
        create_sql = """
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
        """
        self.spark.sql(create_sql)
        logger.info("Created gold.market_dominance table")

    def calculate(self):
        """Calculate market dominance metrics"""
        from datetime import datetime, timedelta

        # Get latest ticker data
        ticker_df = self.spark.table(self.ticker_table)

        # Get latest snapshot per symbol
        window = Window.partitionBy("symbol").orderBy(desc("event_time"))
        latest_df = ticker_df.withColumn("rank", row_number().over(window)) \
                             .filter(col("rank") == 1) \
                             .drop("rank")

        # Calculate market cap (price * volume as proxy)
        market_df = latest_df.withColumn(
            "market_cap",
            col("price_mid") * col("volume_total") * 10
        )

        # Total market metrics
        total_market_cap = market_df.agg(_sum("market_cap")).collect()[0][0] or 1
        total_volume = market_df.agg(_sum("volume_total")).collect()[0][0] or 1

        # BTC dominance
        btc_cap = market_df.filter(col("symbol") == "BTCUSDT") \
                          .agg(_sum("market_cap")).collect()[0][0] or 0
        btc_dominance = (btc_cap / total_market_cap) * 100

        # ETH dominance
        eth_cap = market_df.filter(col("symbol") == "ETHUSDT") \
                          .agg(_sum("market_cap")).collect()[0][0] or 0
        eth_dominance = (eth_cap / total_market_cap) * 100

        # Stablecoin volume
        stablecoins = ["USDCUSDT", "BUSDUSDT", "TUSDUSDT", "DAIUSDT"]
        stablecoin_vol = market_df.filter(col("symbol").isin(stablecoins)) \
                                  .agg(_sum("volume_total")).collect()[0][0] or 0
        stablecoin_pct = (stablecoin_vol / total_volume) * 100

        # Altcoin volume (everything except BTC, ETH, stablecoins)
        major_coins = ["BTCUSDT", "ETHUSDT"] + stablecoins
        altcoin_vol = market_df.filter(~col("symbol").isin(major_coins)) \
                              .agg(_sum("volume_total")).collect()[0][0] or 0
        altcoin_pct = (altcoin_vol / total_volume) * 100

        # Active symbols
        active_symbols = market_df.count()

        # Create result
        result_data = [{
            "snapshot_time": datetime.now(),
            "btc_dominance_pct": round(btc_dominance, 2),
            "eth_dominance_pct": round(eth_dominance, 2),
            "stablecoin_volume_pct": round(stablecoin_pct, 2),
            "altcoin_volume_pct": round(altcoin_pct, 2),
            "total_market_cap": round(total_market_cap, 2),
            "total_volume_24h": round(total_volume, 2),
            "active_symbols": active_symbols,
            "_partition_date": datetime.now().date()
        }]

        result_df = self.spark.createDataFrame(result_data)
        result_df.writeTo(self.gold_table).append()

        logger.info(f"Calculated market dominance: BTC={btc_dominance:.2f}%, ETH={eth_dominance:.2f}%")


class GoldVolatilityRanking:
    """Calculate volatility rankings"""

    def __init__(self, spark: SparkSession):
        self.spark = spark
        self.ticker_table = "iceberg.crypto_lakehouse.silver_ticker_unified"
        self.gold_table = "iceberg.crypto_lakehouse.volatility_ranking"

    def create_table(self):
        """Create Gold volatility_ranking table"""
        create_sql = """
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
        """
        self.spark.sql(create_sql)
        logger.info("Created gold.volatility_ranking table")

    def calculate(self):
        """Calculate volatility rankings"""
        from datetime import datetime, timedelta

        now_ms = int(datetime.now().timestamp() * 1000)
        time_1h_ago = now_ms - (1 * 60 * 60 * 1000)
        time_24h_ago = now_ms - (24 * 60 * 60 * 1000)
        time_7d_ago = now_ms - (7 * 24 * 60 * 60 * 1000)

        ticker_df = self.spark.table(self.ticker_table)

        # Calculate volatility (stddev of price) for different timeframes
        vol_1h = ticker_df.filter(col("event_time") >= time_1h_ago) \
                         .groupBy("symbol").agg(
                             stddev("price_mid").alias("volatility_1h")
                         )

        vol_24h = ticker_df.filter(col("event_time") >= time_24h_ago) \
                          .groupBy("symbol").agg(
                              stddev("price_mid").alias("volatility_24h"),
                              _max("price_mid").alias("high_24h"),
                              _min("price_mid").alias("low_24h")
                          )

        vol_7d = ticker_df.filter(col("event_time") >= time_7d_ago) \
                         .groupBy("symbol").agg(
                             stddev("price_mid").alias("volatility_7d")
                         )

        # Join all timeframes
        result = vol_1h.join(vol_24h, "symbol", "left") \
                      .join(vol_7d, "symbol", "left")

        # Calculate price range %
        result = result.withColumn(
            "price_range_pct_24h",
            when(col("low_24h") > 0,
                 ((col("high_24h") - col("low_24h")) / col("low_24h")) * 100)
            .otherwise(0)
        )

        # Rank by 24h volatility
        result = result.withColumn(
            "rank_by_volatility",
            row_number().over(Window.orderBy(desc("volatility_24h")))
        )

        # Add metadata
        result = result.withColumn("snapshot_time", current_timestamp()) \
                      .withColumn("_partition_date", to_date(current_timestamp())) \
                      .select(
                          "symbol",
                          "snapshot_time",
                          "volatility_1h",
                          "volatility_24h",
                          "volatility_7d",
                          "rank_by_volatility",
                          "price_range_pct_24h",
                          "_partition_date"
                      )

        # Write to Gold
        result.write \
            .format("iceberg") \
            .mode("overwrite") \
            .option("overwrite-mode", "dynamic") \
            .saveAsTable(self.gold_table)

        count = result.count()
        logger.info(f"Calculated volatility rankings for {count} symbols")


class GoldMoversRanking:
    """Calculate top gainers/losers with context"""

    def __init__(self, spark: SparkSession):
        self.spark = spark
        self.ticker_table = "iceberg.crypto_lakehouse.silver_ticker_unified"
        self.gold_table = "iceberg.crypto_lakehouse.movers_ranking"

    def create_table(self):
        """Create Gold movers_ranking table"""
        create_sql = """
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
        """
        self.spark.sql(create_sql)
        logger.info("Created gold.movers_ranking table")

    def calculate(self):
        """Calculate top movers for multiple timeframes"""
        from datetime import datetime

        now_ms = int(datetime.now().timestamp() * 1000)
        timeframes = {
            "1h": now_ms - (1 * 60 * 60 * 1000),
            "24h": now_ms - (24 * 60 * 60 * 1000),
            "7d": now_ms - (7 * 24 * 60 * 60 * 1000)
        }

        ticker_df = self.spark.table(self.ticker_table)

        all_results = []

        for tf_name, tf_start in timeframes.items():
            # Get price at start and end of timeframe
            window_start = Window.partitionBy("symbol").orderBy(asc("event_time"))
            window_end = Window.partitionBy("symbol").orderBy(desc("event_time"))

            df_period = ticker_df.filter(col("event_time") >= tf_start)

            # First and last price
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

            # Calculate change
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

            # Top gainers
            gainers = changes.filter(col("change_pct") > 0) \
                            .orderBy(desc("change_pct")) \
                            .limit(20) \
                            .withColumn("rank", row_number().over(Window.orderBy(desc("change_pct")))) \
                            .withColumn("category", lit("gainer")) \
                            .withColumn("timeframe", lit(tf_name))

            # Top losers
            losers = changes.filter(col("change_pct") < 0) \
                           .orderBy(asc("change_pct")) \
                           .limit(20) \
                           .withColumn("rank", row_number().over(Window.orderBy(asc("change_pct")))) \
                           .withColumn("category", lit("loser")) \
                           .withColumn("timeframe", lit(tf_name))

            # Combine
            movers = gainers.union(losers).select(
                "symbol",
                "rank",
                "category",
                "timeframe",
                "change_pct",
                col("price_end").alias("current_price"),
                col("volume_end").alias("volume_24h"),
                "volume_change_pct"
            )

            all_results.append(movers)

        # Union all timeframes
        final_result = all_results[0]
        for df in all_results[1:]:
            final_result = final_result.union(df)

        # Add metadata
        final_result = final_result.withColumn("snapshot_time", current_timestamp()) \
                                  .withColumn("_partition_date", to_date(current_timestamp()))

        # Write to Gold
        final_result.write \
            .format("iceberg") \
            .mode("overwrite") \
            .option("overwrite-mode", "dynamic") \
            .saveAsTable(self.gold_table)

        count = final_result.count()
        logger.info(f"Calculated movers ranking: {count} entries")
