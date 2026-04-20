# TrustPipe

**AI Data Supply Chain Trust & Provenance Platform**

Track data provenance, detect poisoning, score trust, and generate compliance reports — inside your existing data pipelines.

## The 3-Line Promise

```python
from trustpipe import TrustPipe          # 1. Import
tp = TrustPipe()                          # 2. Initialize (zero-config)
tp.track(df, name="customers")            # 3. Track
```

That's it. Provenance recorded. Merkle chain extended. Query it anytime.

## Why TrustPipe?

- **EU AI Act Article 10** enforcement begins August 2026. Few organizations have the data provenance documentation it requires.
- **87% of AI projects fail** — primary cause: data quality issues.
- **Data poisoning attacks** now target RAG pipelines, fine-tuning data, and MCP tools.

No infrastructure exists to solve all three *inside* the data pipeline. TrustPipe does.

## Three Independent Layers

| Layer | What It Does | Works Alone? |
|-------|-------------|:------------:|
| **Provenance** | Track where data came from (Merkle-backed) | ✓ |
| **Trust** | Score data quality and safety (0-100) | ✓ |
| **Compliance** | Generate regulatory documents (EU AI Act) | ✓ |

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

### Verify Integrity

```bash
trustpipe verify
# Chain integrity: OK
#   Total records: 42
#   Verified: 42
#   Failed: 0
```

### View Lineage

```bash
trustpipe trace clean_customers
# [✓] clean_customers (8000 rows)
#     └── [✓] raw_customers ← s3://bucket/raw/ (10000 rows)
```

## CLI Commands

| Command | Purpose |
|---------|---------|
| `trustpipe init` | Initialize project |
| `trustpipe trace <dataset>` | Show provenance chain |
| `trustpipe verify` | Verify Merkle chain integrity |
| `trustpipe status` | Project summary |
| `trustpipe score <dataset>` | Trust score (0-100) *(Phase 2)* |
| `trustpipe scan <file>` | Poisoning scan *(Phase 2)* |
| `trustpipe comply <dataset>` | Compliance report *(Phase 3)* |

## Design Principles

1. **Zero-config start** — works out of the box with SQLite
2. **Data fingerprinting only** — NEVER stores your raw data
3. **Not blockchain** — Merkle hash tree (same as git), no consensus overhead
4. **LLM-enhanced, not LLM-dependent** — core works fully offline
5. **Pluggable everything** — storage, scoring, compliance templates

## Architecture

```
Your Pipeline (Spark / Airflow / Pandas / dbt)
        │
        ▼
┌────────────────────────────────┐
│         TrustPipe SDK          │
│  ┌──────────┐ ┌──────────────┐ │
│  │Provenance│ │Trust Scoring │ │
│  │(Merkle)  │ │(6 dimensions)│ │
│  └──────────┘ └──────────────┘ │
│  ┌──────────────────────────┐  │
│  │ Compliance Generator     │  │
│  │ (EU AI Act, NIST, SOC 2) │  │
│  └──────────────────────────┘  │
│  Storage: SQLite → Postgres    │
└────────────────────────────────┘
```

## License

Apache 2.0 — open source, enterprise-friendly.
