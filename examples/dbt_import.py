"""TrustPipe — dbt Integration Example.

Demonstrates importing dbt manifest.json for lineage tracking.

Usage:
    # After running `dbt run`:
    python examples/dbt_import.py --manifest target/manifest.json

    # Standalone demo (creates sample manifest):
    python examples/dbt_import.py
"""

import json
import os
import sys

from trustpipe import TrustPipe
from trustpipe.plugins.dbt_plugin import DbtPlugin

# ── Create sample dbt manifest for demo ──────────────────
SAMPLE_MANIFEST = {
    "sources": {
        "source.shop.raw.customers": {
            "name": "customers",
            "source_name": "raw",
            "database": "analytics",
            "schema": "raw",
            "description": "Raw customer registrations",
            "columns": {"id": {}, "name": {}, "email": {}, "created_at": {}},
        },
        "source.shop.raw.orders": {
            "name": "orders",
            "source_name": "raw",
            "database": "analytics",
            "schema": "raw",
            "description": "Raw order transactions",
            "columns": {"id": {}, "customer_id": {}, "amount": {}, "order_date": {}},
        },
    },
    "nodes": {
        "model.shop.stg_customers": {
            "name": "stg_customers",
            "resource_type": "model",
            "database": "analytics",
            "schema": "staging",
            "description": "Staged customers with deduplication",
            "columns": {"customer_id": {}, "name": {}, "email": {}, "first_order_date": {}},
            "depends_on": {"nodes": ["source.shop.raw.customers"]},
            "config": {"materialized": "view"},
            "tags": [],
        },
        "model.shop.stg_orders": {
            "name": "stg_orders",
            "resource_type": "model",
            "database": "analytics",
            "schema": "staging",
            "description": "Staged orders with validation",
            "columns": {"order_id": {}, "customer_id": {}, "amount": {}, "order_date": {}},
            "depends_on": {"nodes": ["source.shop.raw.orders"]},
            "config": {"materialized": "view"},
            "tags": [],
        },
        "model.shop.fct_orders": {
            "name": "fct_orders",
            "resource_type": "model",
            "database": "analytics",
            "schema": "marts",
            "description": "Order facts joined with customer data",
            "columns": {"order_id": {}, "customer_name": {}, "amount": {}, "order_date": {}},
            "depends_on": {"nodes": ["model.shop.stg_customers", "model.shop.stg_orders"]},
            "config": {"materialized": "table"},
            "tags": ["marts"],
        },
    },
}


def main():
    manifest_path = "sample_manifest.json"
    use_sample = True

    # Check if real manifest path provided
    if len(sys.argv) > 1 and sys.argv[1] == "--manifest" and len(sys.argv) > 2:
        manifest_path = sys.argv[2]
        use_sample = False

    # Write sample manifest if needed
    if use_sample:
        with open(manifest_path, "w") as f:
            json.dump(SAMPLE_MANIFEST, f, indent=2)
        print("Using sample dbt manifest for demo\n")

    # ── Import manifest ──────────────────────────────────
    tp = TrustPipe(db_path="dbt_example.db")
    dbt = DbtPlugin(tp)

    print("Importing dbt manifest...")
    records = dbt.import_manifest(manifest_path)
    print(f"✓ Imported {len(records)} records (sources + models)\n")

    # ── View lineage ─────────────────────────────────────
    print("Lineage for fct_orders:")
    lineage = tp.lineage("fct_orders")
    if lineage:
        print(lineage.to_tree_string())

    # ── Trust score ──────────────────────────────────────
    print("\nTrust scores:")
    for name in ["customers", "orders", "stg_customers", "stg_orders", "fct_orders"]:
        chain = tp.trace(name)
        if chain:
            latest = chain[-1]
            score = tp.score(
                {"row_count": latest.row_count, "columns": latest.column_count},
                name=name,
            )
            print(f"  {name:<20} {score.composite}/100 ({score.grade})")

    # ── Compliance ───────────────────────────────────────
    print("\nCompliance gaps for fct_orders:")
    gaps_json = tp.comply("fct_orders", output_format="json")
    gaps = json.loads(gaps_json)["gaps"]
    for g in gaps[:5]:
        print(f"  [{g['severity']}] {g['description']}")

    # ── Verify ───────────────────────────────────────────
    result = tp.verify()
    print(f"\nChain integrity: {result['integrity']} ({result['verified']}/{result['total']})")

    # Cleanup
    os.remove("dbt_example.db")
    if use_sample:
        os.remove(manifest_path)


if __name__ == "__main__":
    main()
