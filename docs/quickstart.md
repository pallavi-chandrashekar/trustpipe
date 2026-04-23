# Quickstart Guide

Get TrustPipe running in under 2 minutes.

## Install

```bash
# Core only (provenance + CLI)
pip install trustpipe

# With trust scoring (recommended)
pip install trustpipe[trust]

# Everything
pip install trustpipe[all]
```

## The 3-Line Promise

```python
from trustpipe import TrustPipe
tp = TrustPipe()
tp.track(df, name="customers", source="s3://bucket/data.csv")
```

That's it. Provenance is recorded in a local SQLite database at `~/.trustpipe/`.

## Track a Pipeline

```python
from trustpipe import TrustPipe
import pandas as pd

tp = TrustPipe()

# Stage 1: Raw data
raw = pd.read_csv("raw_data.csv")
r1 = tp.track(raw, name="raw_customers", source="s3://lake/customers.csv")

# Stage 2: Clean
clean = raw.dropna().drop_duplicates()
r2 = tp.track(clean, name="clean_customers", parent=r1.id)

# Stage 3: Features
features = clean.copy()
features["log_revenue"] = clean["revenue"].apply(lambda x: x + 1)
r3 = tp.track(features, name="customer_features", parent=r2.id)
```

## View Lineage

```python
lineage = tp.lineage("customer_features")
print(lineage.to_tree_string())
# [✓] customer_features (8000 rows)
#     └── [✓] clean_customers (9500 rows)
#         └── [✓] raw_customers ← s3://lake/customers.csv (10000 rows)
```

Or via CLI:
```bash
trustpipe trace customer_features
```

## Trust Score

```python
score = tp.score(features, name="customer_features")
print(score.explain())
# Trust Score: 89/100 (Grade: A)
# Dimensions: Completeness, Consistency, Freshness, Provenance, Drift, Poisoning
```

CLI:
```bash
trustpipe score customer_features
```

## Verify Integrity

```python
result = tp.verify()
# {"integrity": "OK", "verified": 3, "total": 3}
```

CLI:
```bash
trustpipe verify
```

## Compliance Report

```python
report = tp.comply("customer_features", regulation="eu-ai-act-article-10")
print(report)  # Full Article 10 markdown report with gap analysis
```

CLI:
```bash
trustpipe comply customer_features --output report.md
```

## Next Steps

- [Trust Score Guide](trust-score.md) — understand the 6 dimensions
- [EU AI Act Guide](eu-ai-act-guide.md) — compliance documentation
- [Architecture](architecture.md) — how TrustPipe works internally
- [Plugin Development](plugin-development.md) — build custom integrations
