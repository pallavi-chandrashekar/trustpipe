# Architecture

## Overview

TrustPipe is organized into three independent layers, each useful on its own:

```
┌──────────────────────────────────────────────────┐
│ Layer 3: Compliance                               │
│   EU AI Act · Data Cards · Audit Logs · LLM       │
├──────────────────────────────────────────────────┤
│ Layer 2: Trust                                    │
│   6 Dimensions · Drift · Poisoning · Scoring      │
├──────────────────────────────────────────────────┤
│ Layer 1: Provenance                               │
│   Merkle Chain · Records · Lineage · Verification │
├──────────────────────────────────────────────────┤
│ Storage: SQLite · PostgreSQL · S3                  │
├──────────────────────────────────────────────────┤
│ Plugins: Pandas · Spark · Airflow · dbt · Kafka   │
└──────────────────────────────────────────────────┘
```

## Layer 1: Provenance

### Merkle Chain

Every `tp.track()` call:
1. Fingerprints the data (hash of shape, columns, statistics — **never raw data**)
2. Creates a `ProvenanceRecord` with metadata, parent links, and tags
3. Computes a content hash (SHA-256)
4. Appends the hash to a Merkle tree
5. Stores the record + Merkle node in the storage backend

The Merkle tree provides:
- **Tamper evidence** — modifying any historical record changes the root hash
- **O(log n) verification** — prove any record is unmodified without reading all records
- **Append-only guarantee** — records can only be added, never modified

This is the same data structure git uses for commits. Not blockchain — no consensus, no mining, no overhead.

### ProvenanceRecord

```python
@dataclass
class ProvenanceRecord:
    id: str                    # Unique identifier
    name: str                  # Human-readable name
    source: str | None         # Origin URI
    parent_ids: list[str]      # Parent record IDs (lineage)
    fingerprint: str           # SHA-256 of data statistics
    row_count: int | None
    column_names: list[str]
    merkle_root: str           # Chain root after this record
    merkle_index: int          # Position in the chain
    previous_root: str         # Chain root before this record
    tags: list[str]
    metadata: dict
    created_at: datetime
```

### Lineage Graph

Parent-child relationships form a DAG (directed acyclic graph). The `lineage()` method walks this graph to produce a tree visualization.

## Layer 2: Trust

### Six Dimensions

| Dimension | Weight | Algorithm |
|-----------|--------|-----------|
| Provenance Depth | 0.15 | Checks source, parents, Merkle, chain length |
| Freshness | 0.15 | Exponential decay: `exp(-ln(2) * age / half_life)` |
| Completeness | 0.20 | `1 - mean_null_ratio`, penalize low row counts |
| Consistency | 0.20 | Schema drift: missing/extra columns, dtype changes |
| Drift | 0.15 | Statistical tests via evidently (KS/Wasserstein/Jensen-Shannon) |
| Poisoning Risk | 0.15 | Anomaly detection via PyOD (Isolation Forest) |

Composite = weighted sum mapped to 0-100. Grade: A+ (95+), A (85+), B (70+), C (55+), D (40+), F (<40).

### Graceful Degradation

Every dimension works independently. If `evidently` isn't installed, drift returns 0.7 (neutral). If `pyod` isn't installed, poisoning returns 0.7. Core never fails.

## Layer 3: Compliance

### Report Generation

1. Collects all provenance records for a dataset
2. Fetches the latest trust score
3. Builds `Article10Metadata` from records + scores + user-supplied fields
4. Runs gap analysis (10 checks across Articles 10(2) and 10(4))
5. Renders a Jinja2 template (markdown, JSON, or HTML)

### Gap Analysis

Checks for: missing data sources, missing chain of custody, low completeness, no accuracy assessment, no intended use, no geographic scope, no bias methodology, no protected attributes, no governance owner, no preparation methodology.

## Storage

All backends implement the `StorageBackend` abstract class:

| Backend | Use Case | Config |
|---------|----------|--------|
| **SQLite** | Local dev, zero-config | Default, `~/.trustpipe/default.db` |
| **PostgreSQL** | Team collaboration | `PostgresBackend("postgresql://...")` |
| **S3** | Enterprise scale | `S3Backend(bucket="...", prefix="trustpipe")` |

## Plugins

All plugins extend `TrustPipePlugin`:

```python
class TrustPipePlugin(ABC):
    def activate(self) -> None: ...    # Install framework hooks
    def deactivate(self) -> None: ...  # Remove hooks
    def on_read(self, source, data) -> ProvenanceRecord: ...
    def on_write(self, destination, data) -> ProvenanceRecord: ...
```

Plugins **never break user code** — all tracking is wrapped in try/except.
