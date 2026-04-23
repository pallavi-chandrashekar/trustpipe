"""TrustPipe — Spark Integration Example.

Demonstrates tracking Spark DataFrame reads/writes.

Usage:
    pip install trustpipe[spark]
    spark-submit examples/spark_job.py
"""

from trustpipe import TrustPipe

# ── Initialize ───────────────────────────────────────────
tp = TrustPipe(db_path="spark_example.db")

# ── Option 1: Manual tracking (works without plugin) ─────
# Track Spark job inputs/outputs by wrapping your existing code

# Simulate Spark job stats (in a real job, extract from DataFrame)
input_stats = {
    "row_count": 1_000_000,
    "column_count": 15,
    "column_names": ["user_id", "timestamp", "amount", "category"],
}
r1 = tp.track(input_stats, name="raw_events", source="s3://data-lake/events/")
print(f"✓ Tracked input: {r1.row_count} rows")

output_stats = {
    "row_count": 950_000,
    "column_count": 20,
    "column_names": ["user_id", "timestamp", "amount", "category", "log_amount"],
}
r2 = tp.track(output_stats, name="processed_events", parent=r1.id, source="s3://warehouse/events/")
print(f"✓ Tracked output: {r2.row_count} rows, parent={r1.id[:8]}...")

# ── Option 2: Auto-tracking with Spark plugin ────────────
# Uncomment below when running with PySpark available:
#
# from pyspark.sql import SparkSession
# spark = SparkSession.builder.appName("TrustPipe Example").getOrCreate()
#
# # One line activates auto-tracking
# tp.spark(spark)
#
# # All reads/writes are now auto-tracked
# df = spark.read.parquet("s3://data-lake/events/")
# df_clean = df.filter(df.amount > 0).dropDuplicates()
# df_clean.write.parquet("s3://warehouse/events/", mode="overwrite")

# ── Verify ────────────────────────────────────────────────
print(f"\nLineage:")
lineage = tp.lineage("processed_events")
if lineage:
    print(lineage.to_tree_string())

result = tp.verify()
print(f"\nIntegrity: {result['integrity']}")

import os
os.remove("spark_example.db")
