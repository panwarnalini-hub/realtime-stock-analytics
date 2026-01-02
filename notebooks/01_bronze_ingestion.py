# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze Layer - Near Real-Time Stock Ingestion (Micro-Batch)
# MAGIC Batch ingestion of stock quotes with configurable intervals

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
    CHECKPOINT_PATH = "/Volumes/main/stocks/data/checkpoints/bronze"
else:
    BRONZE_PATH = "/tmp/delta/stocks/bronze"
    CHECKPOINT_PATH = "/tmp/delta/stocks/checkpoints/bronze"

# Stock symbols to track
SYMBOLS = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NVDA', 'AMD']

# API Configuration
API_KEY = "LNOMWHFIISN4URI"  # Replace with your key

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.types import *
from delta.tables import DeltaTable
import sys
import time
sys.path.append('/Workspace/Users/panwarnalini@gmail.com/realtime-stock-analytics/src')

from stock_fetcher import StockFetcher

# COMMAND ----------

# Define schema for stock quotes
quote_schema = StructType([
    StructField("symbol", StringType(), False),
    StructField("price", DoubleType(), False),
    StructField("volume", LongType(), False),
    StructField("timestamp", TimestampType(), False),
    StructField("change_percent", DoubleType(), True)
])

# COMMAND ----------

# Create stock fetcher
fetcher = StockFetcher(API_KEY)

# Fetch batch of quotes with rate limiting
quotes = []
print("Fetching stock quotes...")

for symbol in SYMBOLS:
    print(f"Fetching {symbol}...")
    quote = fetcher.get_realtime_quote(symbol)
    if quote:
        quotes.append(quote)
        print(f"  {symbol}: ${quote['price']:.2f} ({quote['change_percent']:.2f}%)")
    time.sleep(15)  # Rate limit: 5 calls per minute (free tier)

print(f"\nFetched {len(quotes)} quotes total")

# COMMAND ----------

# Convert to DataFrame
df = spark.createDataFrame(quotes, schema=quote_schema)

# Add ingestion metadata
bronze_df = df \
    .withColumn("ingestion_timestamp", F.current_timestamp()) \
    .withColumn("ingestion_date", F.current_date()) \
    .withColumn("source", F.lit("alpha_vantage"))

# Write to Bronze Delta table
bronze_df.write \
    .format("delta") \
    .mode("append") \
    .partitionBy("ingestion_date") \
    .save(BRONZE_PATH)

print(f"Ingested {len(quotes)} quotes to Bronze layer at {BRONZE_PATH}")

# COMMAND ----------

# Verify data
bronze_table = spark.read.format("delta").load(BRONZE_PATH)
display(bronze_table.orderBy(F.col("timestamp").desc()).limit(20))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Table Statistics

# COMMAND ----------

print(f"Total records: {bronze_table.count()}")
print(f"Symbols tracked: {bronze_table.select('symbol').distinct().count()}")
print(f"Date range: {bronze_table.agg(F.min('timestamp'), F.max('timestamp')).collect()[0]}")