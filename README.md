<p align="center">
  <img src="assets/logo.svg" alt="TrustPipe" width="400">
</p>

<p align="center">
  <strong>AI Data Supply Chain Trust & Provenance Platform</strong>
</p>

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

## Docker

Run PostgreSQL + API + Dashboard with one command:

```bash
cp .env.example .env        # configure credentials
docker compose up            # starts all 3 services
```

| Service | Port | URL |
|---------|------|-----|
| **API** | 8000 | http://localhost:8000/docs |
| **Dashboard** | 8050 | http://localhost:8050 |
| **PostgreSQL** | 5432 | `postgresql://trustpipe:trustpipe@localhost/trustpipe` |

## Tested on Real Data

TrustPipe is validated against real-world production datasets — not just synthetic examples.

| Dataset | Source | Rows | Trust Score | Key Findings |
|---------|--------|-----:|:-----------:|-------------|
| **UCI Adult Income** | [UCI ML Repository](https://archive.ics.uci.edu/dataset/2/adult) | 48,842 | 77/100 (B) | 7.5% rows with missing values. Poisoning risk flagged. Compliance correctly identified missing bias assessment as CRITICAL (dataset has known gender/race bias) |
| **Credit Card Fraud** | [sklearn](https://scikit-learn.org/) | 50,000 | 75/100 (B) | Drift detected between time periods. Full 5-stage ML pipeline tracked with Merkle verification. Poisoning scan caught injected anomalies |
| **California Housing** | [sklearn](https://scikit-learn.org/stable/datasets/real_world.html#california-housing) | 20,640 | 83/100 (B) | Schema drift detected when columns dropped. Poisoning: 846 baseline anomalies → 884 after injecting 50 bad rows. Full compliance report + data card generated |
| **IMDB Reviews** | [Hugging Face](https://huggingface.co/datasets/imdb) | 5,000 | 89/100 (A) | Text/NLP data tracked correctly through preprocessing pipeline. Chain integrity verified across all stages |

<details>
<summary><b>Expand: UCI Adult Income — Full Results</b></summary>

```
Dataset: UCI Adult Income (1994 Census)
Rows: 48,842 | Columns: 15 | Source: UCI ML Repository

Trust Score: 77/100 (Grade: B)
  Consistency              100.0%
  Freshness                100.0%
  Completeness              99.7%
  Drift                     80.0%
  Provenance Depth          50.0%
  Poisoning Risk            15.5%

Pipeline Test:
  48,842 raw → 45,194 clean (dropped 3,648 rows / 7.5% with '?' values)
  → 6 numeric features extracted

Lineage:
  [✓] adult_features (45,194 rows)
      └── [✓] adult_clean (45,194 rows)
          └── [✓] adult_raw ← uci://adult-income (48,842 rows)

Compliance Gaps (7 total):
  [CRIT] Art. 10(2)(f): No bias assessment methodology documented
  [WARN] Art. 10(2)(b): No accuracy assessment methodology documented
  [WARN] Art. 10(2)(c): Intended use not documented
  [WARN] Art. 10(2)(f): No protected attributes checked for bias
  [WARN] Art. 10(4):    No data governance owner documented
  [INFO] Art. 10(2)(c): Geographic applicability not specified
  [INFO] Art. 10(4):    Data preparation methodology not documented
```
</details>

<details>
<summary><b>Expand: Credit Card Fraud — Full Results</b></summary>

```
Dataset: Credit Card Fraud (sklearn make_classification)
Rows: 50,000 | Features: 28 PCA + Amount + Time | Fraud rate: 2.15%

Trust Score: 75/100 (Grade: B)

Drift Detection:
  Early period score:  75/100
  Late period (3x amount shift): 62/100 (Grade C)
  Drift dimension: detected distribution shift

Poisoning Scan:
  Clean data: anomalies detected in baseline
  After injecting 500 poisoned rows: scanner detected change

Full ML Pipeline Lineage:
  [✓] fraud_train (35,000 rows)
      └── [✓] fraud_features (50,000 rows)
          └── [✓] fraud_clean (50,000 rows)
              └── [✓] fraud_raw ← kaggle://creditcardfraud (50,000 rows)

Chain Integrity: OK (5/5 verified)
```
</details>

<details>
<summary><b>Expand: California Housing — Full Results</b></summary>

```
Dataset: California Housing (1990 Census, sklearn built-in)
Rows: 20,640 | Features: 8 + target | Source: sklearn

Trust Score: 83/100 (Grade: B)
  Completeness             100.0%
  Consistency              100.0%
  Freshness                100.0%
  Drift                     80.0%
  Poisoning Risk            59.0%
  Provenance Depth          50.0%

Feature Engineering Pipeline:
  20,640 raw → 20,640 features (12 cols: +rooms_per_household,
  bedrooms_ratio, population_density) → normalized → 16,512 train

Lineage:
  [✓] housing_train (16,512 rows)
      └── [✓] housing_normalized (20,640 rows)
          └── [✓] housing_features (20,640 rows)
              └── [✓] housing_raw ← sklearn://california-housing (20,640 rows)

Schema Drift Test:
  V1: 9 cols, score 83/100
  V2: 7 cols (dropped 2), score 92/100 — drift detected

Poisoning Scan:
  Baseline: 846/20,640 flagged
  After injecting 50 rows (500 rooms, $0 value): 884/20,640 flagged

Compliance: 7 gaps (1 critical), full Article 10 report + data card + audit log generated
```
</details>

<details>
<summary><b>Expand: IMDB Reviews — Full Results</b></summary>

```
Dataset: IMDB Movie Reviews (Hugging Face)
Rows: 5,000 | Columns: text, label | Source: huggingface://imdb

Trust Score: 89/100 (Grade: A)

NLP Pipeline:
  5,000 raw → 5,000 preprocessed (lowercase + truncate + text_length)
  → 4,000 train split

Chain Integrity: OK (3/3 verified)

Demonstrates TrustPipe works with text/NLP data, not just tabular.
```
</details>

See [full test results](RESULTS.md) for detailed analysis. Run the tests yourself:

```bash
pip install trustpipe[dev] ucimlrepo datasets
pytest tests/e2e/test_real_datasets.py -v -s
```

## Architecture

```
Your Pipeline (Spark / Airflow / Pandas / dbt / Kafka)
        │
        ▼
┌──────────────────────────────────────────┐
│            TrustPipe SDK                 │
│                                          │
│  Layer 1: Provenance                     │
│  ┌────────────────────────────────────┐  │
│  │ Merkle chain · Lineage DAG · Tags  │  │
│  └────────────────────────────────────┘  │
│                                          │
│  Layer 2: Trust                          │
│  ┌────────────────────────────────────┐  │
│  │ 6 dimensions · Drift · Poisoning   │  │
│  └────────────────────────────────────┘  │
│                                          │
│  Layer 3: Compliance                     │
│  ┌────────────────────────────────────┐  │
│  │ EU AI Act · Data Cards · Audits    │  │
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
make test          # full suite (138 tests)
make test-quick    # unit tests only
make lint          # ruff check
```

## License

Apache 2.0 — open source, enterprise-friendly.
