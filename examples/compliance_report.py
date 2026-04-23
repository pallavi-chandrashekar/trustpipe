"""TrustPipe — EU AI Act Compliance Report Example.

Demonstrates generating Article 10 compliance documentation.

Usage:
    pip install trustpipe[trust]
    python examples/compliance_report.py
"""

import pandas as pd
import numpy as np

from trustpipe import TrustPipe

# ── Setup: track a pipeline ──────────────────────────────
tp = TrustPipe(db_path="compliance_example.db")
np.random.seed(42)

# Simulate a ML training pipeline
raw = pd.DataFrame({
    "customer_id": range(10000),
    "credit_score": np.random.normal(650, 100, 10000).astype(int),
    "income": np.random.lognormal(10, 0.5, 10000).round(2),
    "age": np.random.randint(18, 80, 10000),
    "default": np.random.choice([0, 1], 10000, p=[0.95, 0.05]),
})

r1 = tp.track(raw, name="raw_credit_data", source="jdbc://prod-db/credit_applications")
r2 = tp.track(
    raw.dropna(),
    name="training_data",
    parent=r1.id,
    source="pipeline://ml/credit-model",
    tags=["training", "pii"],
)

# Score the training data
score = tp.score(raw, name="training_data")
print(f"Trust Score: {score.composite}/100 ({score.grade})\n")

# ── Generate EU AI Act Article 10 Report ─────────────────
print("=" * 60)
print("EU AI Act Article 10 Compliance Report")
print("=" * 60)

report = tp.comply(
    "training_data",
    regulation="eu-ai-act-article-10",
    user_metadata={
        "intended_use": "Credit default prediction model for loan underwriting",
        "geographic_applicability": "United States, European Union",
        "population_coverage": "Adults aged 18-80 with credit history",
        "known_limitations": [
            "Training data is US-centric, may not generalize to EU markets",
            "Age distribution skews younger than general population",
        ],
    },
)
print(report)

# ── Generate Data Card ───────────────────────────────────
print("\n" + "=" * 60)
print("Data Card")
print("=" * 60)

datacard = tp.comply("training_data", regulation="datacard")
print(datacard)

# ── Gap Analysis (JSON) ─────────────────────────────────
import json

print("\n" + "=" * 60)
print("Compliance Gap Analysis")
print("=" * 60)

gaps_json = tp.comply("training_data", output_format="json")
gaps = json.loads(gaps_json)["gaps"]

for g in gaps:
    severity_icon = {"CRITICAL": "!!", "WARNING": "!", "INFO": "i"}
    print(f"  [{severity_icon.get(g['severity'], '?')}] {g['article_ref']}: {g['description']}")
    if g.get("recommendation"):
        print(f"      -> {g['recommendation']}")

print(f"\nTotal: {len(gaps)} gaps")

# ── Save report to file ─────────────────────────────────
with open("article10_report.md", "w") as f:
    f.write(report)
print(f"\n✓ Report saved to article10_report.md")

# Cleanup
import os
os.remove("compliance_example.db")
os.remove("article10_report.md")
