"""TrustPipe Quickstart — Pandas Integration.

Demonstrates the 3-line promise + trust scoring + auto-tracking.

Usage:
    pip install trustpipe[trust]
    python examples/pandas_quickstart.py
"""

import pandas as pd
import numpy as np

from trustpipe import TrustPipe

# ── 1. Initialize (zero-config) ─────────────────────────
tp = TrustPipe(db_path="quickstart.db")
print("✓ TrustPipe initialized\n")

# ── 2. Create sample data ───────────────────────────────
np.random.seed(42)
raw_df = pd.DataFrame({
    "user_id": range(5000),
    "amount": np.random.lognormal(4, 1, 5000).round(2),
    "category": np.random.choice(["electronics", "food", "clothing"], 5000),
})
print(f"Raw data: {raw_df.shape[0]} rows, {raw_df.shape[1]} columns")

# ── 3. Track raw data (the 3-line promise) ───────────────
r1 = tp.track(raw_df, name="raw_orders", source="s3://data-lake/orders.parquet")
print(f"✓ Tracked raw_orders: ID={r1.id}, Merkle={r1.merkle_root[:12]}...\n")

# ── 4. Transform and track ───────────────────────────────
clean_df = raw_df[raw_df["amount"] > 0].drop_duplicates()
r2 = tp.track(clean_df, name="clean_orders", parent=r1.id)
print(f"✓ Tracked clean_orders: {r2.row_count} rows, parent={r1.id[:8]}...")

features_df = clean_df.copy()
features_df["log_amount"] = np.log1p(features_df["amount"])
r3 = tp.track(features_df, name="order_features", parent=r2.id)
print(f"✓ Tracked order_features: {r3.row_count} rows, {r3.column_count} columns\n")

# ── 5. View lineage ─────────────────────────────────────
print("Lineage tree:")
lineage = tp.lineage("order_features")
print(lineage.to_tree_string())

# ── 6. Trust score ──────────────────────────────────────
print("\nTrust score:")
score = tp.score(features_df, name="order_features")
print(score.explain())

# ── 7. Verify chain integrity ───────────────────────────
result = tp.verify()
print(f"\nChain integrity: {result['integrity']} ({result['verified']}/{result['total']} verified)")

# ── 8. Auto-tracking with Pandas plugin ─────────────────
print("\n--- Pandas Auto-Tracking ---")
plugin = tp.pandas()

# These are automatically tracked — no manual tp.track() needed
features_df.head(100).to_csv("/tmp/trustpipe_example.csv", index=False)
auto_df = pd.read_csv("/tmp/trustpipe_example.csv")
print(f"✓ Auto-tracked: read_csv ({auto_df.shape[0]} rows)")

plugin.deactivate()

# ── Cleanup ─────────────────────────────────────────────
import os
os.remove("quickstart.db")
os.remove("/tmp/trustpipe_example.csv")
print("\n✓ Done! Cleaned up temp files.")
