# Databricks notebook source
# MAGIC %md
# MAGIC # Gold Layer - Business Analytics
# MAGIC Generate business-ready insights

# COMMAND ----------
# MAGIC %md
# MAGIC ## Configuration
# MAGIC 
# MAGIC **Path Configuration:**
# MAGIC - Community Edition (Unity Catalog): Use `/Volumes/main/stocks/data/`
# MAGIC - Standard/Premium (DBFS): Use `/tmp/delta/stocks/` or `/dbfs/FileStore/stocks/`
# MAGIC 
# MAGIC Update the paths below based on your environment.

# COMMAND ----------

# Environment configuration
USE_UNITY_CATALOG = True  # Set to False for DBFS-enabled workspaces

if USE_UNITY_CATALOG:
    SILVER_PATH = "/Volumes/main/stocks/data/silver"
    GOLD_PATH = "/Volumes/main/stocks/data/gold"
else:
    SILVER_PATH = "/tmp/delta/stocks/silver"
    GOLD_PATH = "/tmp/delta/stocks/gold"

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window

# COMMAND ----------

# Read Silver data
silver_df = spark.read.format("delta").load(SILVER_PATH)

print(f"Reading {silver_df.count()} records from Silver layer")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Top Movers Analysis

# COMMAND ----------

# Get latest data for each symbol
latest_window = Window.partitionBy("symbol").orderBy(F.col("timestamp").desc())

latest_quotes = silver_df \
    .withColumn("rank", F.row_number().over(latest_window)) \
    .filter(F.col("rank") == 1) \
    .select(
        "symbol",
        "price",
        "change_percent",
        "volume",
        "ma_1hr",
        "volatility",
        "timestamp"
    )

# Identify top gainers and losers
top_movers = latest_quotes \
    .withColumn("movement_type",
                F.when(F.col("change_percent") > 2, "Strong Gainer")
                .when(F.col("change_percent") > 0, "Gainer")
                .when(F.col("change_percent") < -2, "Strong Loser")
                .when(F.col("change_percent") < 0, "Loser")
                .otherwise("Neutral"))

# COMMAND ----------

display(top_movers.orderBy(F.col("change_percent").desc()))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Volatility Leaders

# COMMAND ----------

volatility_leaders = latest_quotes \
    .filter(F.col("volatility").isNotNull()) \
    .orderBy(F.col("volatility").desc()) \
    .select(
        "symbol",
        "price",
        F.round("volatility", 2).alias("volatility_pct"),
        "volume"
    )

display(volatility_leaders)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Price Alerts

# COMMAND ----------

# Generate alerts for significant price movements
alerts = latest_quotes \
    .filter(
        (F.abs(F.col("change_percent")) > 3) |  # >3% change
        (F.col("volatility") > 5)  # High volatility
    ) \
    .withColumn("alert_type",
                F.when(F.col("change_percent") > 3, "SPIKE")
                .when(F.col("change_percent") < -3, "DROP")
                .when(F.col("volatility") > 5, "HIGH_VOLATILITY")
                .otherwise("NORMAL")) \
    .withColumn("alert_timestamp", F.current_timestamp())

display(alerts)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Write to Gold Layer

# COMMAND ----------

# Write analytics to Gold layer
top_movers.write.format("delta").mode("overwrite").save(f"{GOLD_PATH}/top_movers")
print(f"Written top movers to {GOLD_PATH}/top_movers")

volatility_leaders.write.format("delta").mode("overwrite").save(f"{GOLD_PATH}/volatility")
print(f"Written volatility leaders to {GOLD_PATH}/volatility")

alerts.write.format("delta").mode("overwrite").save(f"{GOLD_PATH}/alerts")
print(f"Written alerts to {GOLD_PATH}/alerts")

print("\nGold layer analytics complete")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary Statistics

# COMMAND ----------

print(f"Top Movers: {top_movers.count()} symbols")
print(f"High Volatility: {volatility_leaders.filter(F.col('volatility_pct') > 3).count()} symbols")
print(f"Active Alerts: {alerts.count()} alerts")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold Layer Verification

# COMMAND ----------

# Verify all Gold tables
print("Gold Layer Tables:")
print(f"1. Top Movers: {spark.read.format('delta').load(f'{GOLD_PATH}/top_movers').count()} records")
print(f"2. Volatility Leaders: {spark.read.format('delta').load(f'{GOLD_PATH}/volatility').count()} records")
print(f"3. Alerts: {spark.read.format('delta').load(f'{GOLD_PATH}/alerts').count()} records")