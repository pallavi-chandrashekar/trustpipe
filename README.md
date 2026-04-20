# TrustPipe

**AI Data Supply Chain Trust & Provenance Platform**

Track data provenance, score trust, detect poisoning, and generate compliance reports — inside your existing data pipelines.

[![Tests](https://github.com/pallavi-chandrashekar/trustpipe/actions/workflows/test.yml/badge.svg)](https://github.com/pallavi-chandrashekar/trustpipe/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)

## The 3-Line Promise

```python
from trustpipe import TrustPipe          # 1. Import
tp = TrustPipe()                          # 2. Initialize (zero-config)
tp.track(df, name="customers")            # 3. Track
```

That's it. Provenance recorded. Merkle chain extended. Trust scored. Query anytime.

## Why TrustPipe?

| Problem | Impact |
|---------|--------|
| **EU AI Act Article 10** enforcement begins August 2026 | Few orgs have data provenance docs |
| **87% of AI projects fail** — primary cause: data quality | $406M avg annual loss per org |
| **Data poisoning attacks** now target RAG, fine-tuning, MCP tools | Most orgs have zero detection |

No infrastructure exists to solve all three *inside* the data pipeline. TrustPipe does.

## Three Independent Layers

| Layer | What It Does | Works Alone? |
|-------|-------------|:------------:|
| **Provenance** | Track where data came from (Merkle-backed, tamper-evident) | ✓ |
| **Trust** | Score data quality and safety (0-100, six dimensions) | ✓ |
| **Compliance** | Generate regulatory documents (EU AI Act, data cards) | ✓ |

## Quick Start

```bash
pip install trustpipe
```

### Track Data Provenance

```python
from trustpipe import TrustPipe

tp = TrustPipe()

# Track a raw dataset
raw = tp.track(df_raw, name="raw_customers", source="s3://bucket/raw/")

# Track a transformation with parent linkage
clean = tp.track(df_clean, name="clean_customers", parent=raw.id)

# View the full chain
for record in tp.trace("clean_customers"):
    print(f"{record.name} ← {record.source} ({record.row_count} rows)")
```

### Trust Scoring (0-100)

```python
score = tp.score(df, name="customers")
print(score.explain())
# Trust Score: 95/100 (Grade: A+)
#
#   Completeness           ████████████████████ 100.0 (w=0.20)
#   Consistency            ████████████████████ 100.0 (w=0.20)
#   Poisoning Risk         ████████████████████ 100.0 (w=0.15)
#   Freshness              ████████████████████ 100.0 (w=0.15)
#   Drift                  ████████████████░░░░  80.0 (w=0.15)
#   Provenance Depth       ██████████████░░░░░░  70.0 (w=0.15)
```

Six dimensions: **Provenance Depth**, **Freshness**, **Completeness**, **Consistency**, **Drift**, **Poisoning Risk**.

### Poisoning Scan

```python
result = tp.scan(df)
# 0 anomalies / 10000 rows (zscore fallback)
# With PyOD installed: Isolation Forest detection
```

### Drift Detection

```python
score = tp.score(new_data, name="features", reference=baseline_data)
# Drift dimension drops when distributions shift
```

### EU AI Act Compliance Report

```python
report = tp.comply("training_set", regulation="eu-ai-act-article-10")
# Generates full Article 10 report with gap analysis:
# - Data sources & lineage (Art. 10(2)(a))
# - Quality metrics (Art. 10(2)(b))
# - Bias assessment (Art. 10(2)(f))
# - 10-point compliance gap analysis with recommendations
```

Also supports `datacard` and `audit-log` report types.

### Pandas Auto-Tracking

```python
tp.pandas()  # activate once

df = pd.read_csv("data.csv")          # auto-tracked
df.to_parquet("output.parquet")        # auto-tracked
```

### Airflow Integration

```python
from trustpipe.plugins.airflow_plugin import trustpipe_task

@trustpipe_task(tp, name="etl_output", inputs=["raw_data"])
@task
def transform(data):
    return processed_data  # auto-tracked with parent linkage
```

### dbt Integration

```python
from trustpipe.plugins.dbt_plugin import DbtPlugin

dbt = DbtPlugin(tp)
dbt.import_manifest("target/manifest.json")    # imports full lineage
dbt.import_run_results("target/run_results.json")  # tracks execution
```

### REST API

```bash
trustpipe serve --port 8000
# POST /track, GET /trace/{name}, GET /score/{name}
# GET /comply/{name}, GET /verify, GET /export
# Auto-generated docs at /docs
```

### Web Dashboard

```bash
trustpipe dashboard --port 8050
# Overview: trust score gauges per dataset
# Records: searchable/sortable provenance table
# Compliance: gap summary across all datasets
```

### CI/CD Trust Gate

```bash
# Fail CI if trust score < threshold
trustpipe gate training_set --threshold 70
# Exit 0 = PASS, Exit 1 = FAIL
```

GitHub Actions workflow included — see `.github/workflows/trust-gate.yml`.

### Multi-Project Federation

```python
from trustpipe.core.federation import Federation

fed = Federation([prod_tp, staging_tp, ml_tp])
fed.status()                    # unified status across all projects
fed.search("customers")         # find dataset across all projects
fed.verify_all()                # integrity check everywhere
```

### Webhook / Slack Alerts

```python
from trustpipe.alerts.webhook import AlertManager, SlackAlert

alerts = AlertManager()
alerts.add(SlackAlert(webhook_url="https://hooks.slack.com/..."))
alerts.check_score("training_set", score, threshold=70)   # alerts on drop
alerts.check_integrity(verify_result)                       # alerts on failure
```

## CLI Commands

| Command | Purpose |
|---------|---------|
| `trustpipe init` | Initialize project |
| `trustpipe trace <dataset>` | Show provenance chain (tree/table/json) |
| `trustpipe verify` | Verify Merkle chain integrity |
| `trustpipe status` | Project summary |
| `trustpipe score <dataset>` | Trust score (0-100) with dimension breakdown |
| `trustpipe scan <file>` | Poisoning / anomaly scan |
| `trustpipe comply <dataset>` | Compliance report (EU AI Act, datacard, audit-log) |
| `trustpipe export` | Export provenance data (JSON/CSV) |
| `trustpipe gate <dataset>` | CI/CD trust gate (exit 1 if below threshold) |
| `trustpipe dashboard` | Launch web dashboard |
| `trustpipe serve` | Launch REST API server |

## Installation

```bash
# Core only (provenance + CLI, 5 lightweight deps)
pip install trustpipe

# With trust scoring (adds pandas, numpy)
pip install trustpipe[trust]

# With drift detection
pip install trustpipe[drift]

# With poisoning detection
pip install trustpipe[poisoning]

# Plugins
pip install trustpipe[spark]      # PySpark integration
pip install trustpipe[api]        # FastAPI REST server
pip install trustpipe[dashboard]  # Plotly Dash web UI

# Everything
pip install trustpipe[all]

# Development
pip install trustpipe[dev]
```

## Storage Backends

| Backend | Use Case | Config |
|---------|----------|--------|
| **SQLite** (default) | Local dev, single user | Zero-config, `~/.trustpipe/` |
| **PostgreSQL** | Team collaboration | `pip install trustpipe[postgres]` |
| **S3** | Enterprise scale | `pip install trustpipe[s3]` |

## Architecture

```
Your Pipeline (Spark / Airflow / Pandas / dbt / Kafka)
        │
        ▼
┌──────────────────────────────────────────┐
│            TrustPipe SDK                  │
│                                          │
│  Layer 1: Provenance                     │
│  ┌────────────────────────────────────┐  │
│  │ Merkle chain · Lineage DAG · Tags │  │
│  └────────────────────────────────────┘  │
│                                          │
│  Layer 2: Trust                          │
│  ┌────────────────────────────────────┐  │
│  │ 6 dimensions · Drift · Poisoning  │  │
│  └────────────────────────────────────┘  │
│                                          │
│  Layer 3: Compliance                     │
│  ┌────────────────────────────────────┐  │
│  │ EU AI Act · Data Cards · Audits   │  │
│  └────────────────────────────────────┘  │
│                                          │
│  Plugins: Pandas·Spark·Airflow·dbt·Kafka │
│  Storage: SQLite · PostgreSQL · S3       │
│  Alerts:  Webhook · Slack                │
│  Serve:   REST API · Web Dashboard       │
└──────────────────────────────────────────┘
```

## Design Principles

1. **Zero-config start** — works out of the box with SQLite
2. **3-line integration** — no rewriting existing pipelines
3. **Data fingerprinting only** — NEVER stores your raw data
4. **Not blockchain** — Merkle hash tree (same as git), zero overhead
5. **LLM-enhanced, not LLM-dependent** — core works fully offline
6. **Graceful degradation** — missing optional deps return neutral scores, never crash
7. **Pluggable everything** — storage, scoring, compliance templates, alert destinations

## Testing

```bash
make test          # full suite (118 tests)
make test-quick    # unit tests only
make lint          # ruff check
```

## License

Apache 2.0 — open source, enterprise-friendly.
