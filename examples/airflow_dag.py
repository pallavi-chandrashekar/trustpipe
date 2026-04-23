"""TrustPipe — Airflow DAG Example.

Demonstrates the @trustpipe_task decorator for provenance tracking.

Usage:
    Copy this file to your Airflow DAGs folder.
    Or run standalone: python examples/airflow_dag.py
"""

from trustpipe import TrustPipe
from trustpipe.plugins.airflow_plugin import trustpipe_task

# ── Initialize ───────────────────────────────────────────
tp = TrustPipe(db_path="airflow_example.db")

# ── Simulate Airflow tasks with @trustpipe_task ──────────
# In a real Airflow DAG, you'd also use @task from airflow.decorators


@trustpipe_task(tp, name="extract_customers", tags=["extract"])
def extract():
    """Extract raw customer data."""
    return {"row_count": 10000, "source": "postgresql://prod/customers"}


@trustpipe_task(tp, name="transform_customers", inputs=["extract_customers"], tags=["transform"])
def transform(raw_data):
    """Clean and transform customer data."""
    return {"row_count": 9500, "nulls_removed": 500}


@trustpipe_task(tp, name="load_features", inputs=["transform_customers"], tags=["load"])
def load(clean_data):
    """Load features into feature store."""
    return {"row_count": 9500, "destination": "s3://features/customers/"}


# ── Run the "DAG" ────────────────────────────────────────
print("Running simulated Airflow DAG...\n")

raw = extract()
print(f"  extract: {raw}")

clean = transform(raw)
print(f"  transform: {clean}")

features = load(clean)
print(f"  load: {features}")

# ── View results ─────────────────────────────────────────
print("\nLineage tree:")
lineage = tp.lineage("load_features")
if lineage:
    print(lineage.to_tree_string())

print(f"\nProvenance records: {tp.status()['record_count']}")
result = tp.verify()
print(f"Chain integrity: {result['integrity']}")

import os
os.remove("airflow_example.db")
