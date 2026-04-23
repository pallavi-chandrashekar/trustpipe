# Changelog

All notable changes to TrustPipe will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-04-23

### Added

**Layer 1: Provenance**
- Merkle-backed append-only provenance chain (tamper-evident)
- `track()` — record data assets with source, parent linkage, tags, metadata
- `trace()` — view full provenance chain for any dataset
- `verify()` — O(log n) Merkle chain integrity verification
- `lineage()` — DAG visualization of data lineage
- Pure-Python Merkle tree (zero external dependencies required)
- ProvenanceRecord with SHA-256 fingerprinting (never stores raw data)

**Layer 2: Trust Scoring**
- 0-100 composite trust score across 6 dimensions
- Provenance Depth, Freshness, Completeness, Consistency, Drift, Poisoning Risk
- Drift detection via evidently (KS/Wasserstein/Jensen-Shannon) with simple fallback
- Poisoning scan via PyOD Isolation Forest with z-score fallback
- Configurable dimension weights
- Graceful degradation when optional deps not installed

**Layer 3: Compliance**
- EU AI Act Article 10 compliance report with 10-point gap analysis
- Data Card report generation
- Audit Log report generation
- Jinja2 templates (markdown, JSON output)
- Optional LLM-enhanced narrative generation (Anthropic Claude / OpenAI)

**Plugins**
- Pandas — auto-tracks `pd.read_csv`, `df.to_parquet`, etc.
- Spark — DataFrameReader/Writer wrapping
- Airflow — `@trustpipe_task` decorator with parent linkage
- dbt — manifest.json import + run_results tracking
- Kafka — TrackedConsumer/TrackedProducer wrappers

**Storage Backends**
- SQLite (default, zero-config)
- PostgreSQL (team collaboration, psycopg3)
- S3 (enterprise scale, boto3)

**Platform**
- REST API (FastAPI) — 10 endpoints with auto-generated docs
- Web Dashboard (Plotly Dash) — trust gauges, records table, compliance overview
- CI/CD Trust Gate — `trustpipe gate` exits non-zero if below threshold
- GitHub Actions workflow for trust gate integration
- Webhook + Slack alerts on score drops and integrity failures
- Multi-project federation — cross-project search, trace, verify

**CLI (11 commands)**
- `trustpipe init`, `trace`, `verify`, `status`
- `trustpipe score`, `scan`
- `trustpipe comply`, `export`
- `trustpipe gate`
- `trustpipe dashboard`, `serve`

**Testing**
- 138 tests (118 unit/integration + 20 real dataset e2e)
- Validated on UCI Adult Income (48K rows), Credit Card Fraud (50K),
  California Housing (20K), IMDB Reviews (5K)
- GitHub Actions CI across Python 3.10-3.13

**Documentation**
- Quickstart guide
- Architecture overview
- Trust score deep dive
- EU AI Act compliance guide
- Plugin development guide
- 5 runnable examples
- CONTRIBUTING.md

**Infrastructure**
- Docker Compose (PostgreSQL + API + Dashboard)
- PyPI package (`pip install trustpipe`)
- Apache 2.0 license
