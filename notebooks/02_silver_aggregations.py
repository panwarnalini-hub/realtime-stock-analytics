# Databricks notebook source
# MAGIC %md
# MAGIC # Silver Layer - Data Quality & Aggregations
# MAGIC Clean data and calculate technical indicators

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
    BRONZE_PATH = "/Volumes/main/stocks/data/bronze"
    SILVER_PATH = "/Volumes/main/stocks/data/silver"
else:
    BRONZE_PATH = "/tmp/delta/stocks/bronze"
    SILVER_PATH = "/tmp/delta/stocks/silver"

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window
from delta.tables import DeltaTable

# COMMAND ----------

# Read Bronze data
bronze_df = spark.read.format("delta").load(BRONZE_PATH)

print(f"Reading {bronze_df.count()} records from Bronze layer")

# COMMAND ----------

# Data quality checks
silver_df = bronze_df \
    .filter(F.col("price") > 0) \
    .filter(F.col("volume") >= 0) \
    .dropDuplicates(["symbol", "timestamp"])

print(f"After data quality checks: {silver_df.count()} records")

# COMMAND ----------

# Calculate moving averages
window_5min = Window.partitionBy("symbol").orderBy("timestamp").rowsBetween(-4, 0)
window_15min = Window.partitionBy("symbol").orderBy("timestamp").rowsBetween(-14, 0)
window_1hr = Window.partitionBy("symbol").orderBy("timestamp").rowsBetween(-59, 0)

silver_enriched = silver_df \
    .withColumn("ma_5min", F.avg("price").over(window_5min)) \
    .withColumn("ma_15min", F.avg("price").over(window_15min)) \
    .withColumn("ma_1hr", F.avg("price").over(window_1hr)) \
    .withColumn("volume_avg_1hr", F.avg("volume").over(window_1hr)) \
    .withColumn("price_stddev_1hr", F.stddev("price").over(window_1hr))

# COMMAND ----------

# Calculate volatility
silver_enriched = silver_enriched \
    .withColumn("volatility", 
                F.when(F.col("ma_1hr") > 0, 
                      (F.col("price_stddev_1hr") / F.col("ma_1hr")) * 100)
                .otherwise(0))

# Add quality score
silver_enriched = silver_enriched \
    .withColumn("data_quality_score",
                F.when((F.col("price").isNotNull()) & 
                      (F.col("volume") > 0) &
                      (F.col("volatility") < 50), 100)
                .when((F.col("price").isNotNull()) & 
                      (F.col("volume") > 0), 80)
                .otherwise(50))

# COMMAND ----------

# Write to Silver Delta table
silver_enriched.write \
    .format("delta") \
    .mode("overwrite") \
    .partitionBy("ingestion_date", "symbol") \
    .save(SILVER_PATH)

print(f"Processed {silver_enriched.count()} records to Silver layer at {SILVER_PATH}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verification

# COMMAND ----------

# Display sample
silver_table = spark.read.format("delta").load(SILVER_PATH)
display(silver_table.orderBy(F.col("timestamp").desc()).limit(20))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Table Statistics

# COMMAND ----------

print(f"Total records: {silver_table.count()}")
print(f"Symbols tracked: {silver_table.select('symbol').distinct().count()}")
print(f"Average volatility: {silver_table.agg(F.avg('volatility')).collect()[0][0]:.2f}%")
print(f"Average quality score: {silver_table.agg(F.avg('data_quality_score')).collect()[0][0]:.1f}")