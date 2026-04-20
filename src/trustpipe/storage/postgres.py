"""PostgreSQL storage backend — team/enterprise use.

Requires: pip install trustpipe[postgres]
Connection string via config or env var TRUSTPIPE_STORAGE_PATH:
  postgresql://user:pass@host:5432/trustpipe
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from trustpipe.core.exceptions import StorageError
from trustpipe.provenance.record import ProvenanceRecord
from trustpipe.storage.base import StorageBackend

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS provenance_records (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    source          TEXT,
    parent_ids      JSONB DEFAULT '[]',
    fingerprint     TEXT NOT NULL,
    row_count       INTEGER,
    column_count    INTEGER,
    column_names    JSONB DEFAULT '[]',
    byte_size       BIGINT,
    statistical_summary JSONB DEFAULT '{}',
    merkle_root     TEXT NOT NULL,
    merkle_index    INTEGER NOT NULL,
    previous_root   TEXT,
    tags            JSONB DEFAULT '[]',
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL,
    data_timestamp  TIMESTAMPTZ,
    project         TEXT NOT NULL DEFAULT 'default'
);

CREATE INDEX IF NOT EXISTS idx_pg_prov_name ON provenance_records(name);
CREATE INDEX IF NOT EXISTS idx_pg_prov_project ON provenance_records(project);
CREATE INDEX IF NOT EXISTS idx_pg_prov_created ON provenance_records(created_at);

CREATE TABLE IF NOT EXISTS trust_scores (
    id              TEXT PRIMARY KEY,
    record_id       TEXT,
    dataset_name    TEXT,
    composite       INTEGER NOT NULL,
    grade           TEXT NOT NULL,
    dimensions      JSONB NOT NULL,
    warnings        JSONB DEFAULT '[]',
    computed_at     TIMESTAMPTZ NOT NULL,
    config_snapshot JSONB DEFAULT '{}',
    project         TEXT NOT NULL DEFAULT 'default'
);

CREATE INDEX IF NOT EXISTS idx_pg_trust_dataset ON trust_scores(dataset_name);

CREATE TABLE IF NOT EXISTS compliance_reports (
    id              TEXT PRIMARY KEY,
    dataset_name    TEXT NOT NULL,
    regulation      TEXT NOT NULL,
    content         TEXT NOT NULL,
    output_format   TEXT NOT NULL,
    generated_at    TIMESTAMPTZ NOT NULL,
    record_ids      JSONB DEFAULT '[]',
    trust_score_id  TEXT,
    project         TEXT NOT NULL DEFAULT 'default'
);

CREATE TABLE IF NOT EXISTS merkle_nodes (
    idx             INTEGER NOT NULL,
    hash            TEXT NOT NULL,
    project         TEXT NOT NULL DEFAULT 'default',
    PRIMARY KEY (project, idx)
);

CREATE TABLE IF NOT EXISTS schema_version (
    version         INTEGER PRIMARY KEY,
    applied_at      TIMESTAMPTZ NOT NULL
);
"""


class PostgresBackend(StorageBackend):
    """PostgreSQL storage backend using psycopg3.

    Usage:
        from trustpipe.storage.postgres import PostgresBackend
        backend = PostgresBackend("postgresql://user:pass@localhost/trustpipe")
        tp = TrustPipe(storage=backend)
    """

    def __init__(self, conninfo: str) -> None:
        self._conninfo = conninfo
        self._conn = None

    def _get_conn(self):
        if self._conn is None or self._conn.closed:
            try:
                import psycopg
            except ImportError:
                raise ImportError("PostgreSQL backend requires psycopg: pip install trustpipe[postgres]")
            self._conn = psycopg.connect(self._conninfo, autocommit=False)
        return self._conn

    def initialize(self) -> None:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(SCHEMA_SQL)
                cur.execute(
                    "INSERT INTO schema_version (version, applied_at) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (1, datetime.now(timezone.utc)),
                )
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise StorageError(f"PostgreSQL migration failed: {e}") from e

    # ── Provenance ────────────────────────────────────────────

    def save_provenance_record(self, record: ProvenanceRecord) -> None:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO provenance_records
                       (id, name, source, parent_ids, fingerprint, row_count,
                        column_count, column_names, byte_size, statistical_summary,
                        merkle_root, merkle_index, previous_root, tags, metadata,
                        created_at, data_timestamp, project)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        record.id, record.name, record.source,
                        json.dumps(record.parent_ids), record.fingerprint,
                        record.row_count, record.column_count,
                        json.dumps(record.column_names), record.byte_size,
                        json.dumps(record.statistical_summary),
                        record.merkle_root, record.merkle_index, record.previous_root,
                        json.dumps(record.tags), json.dumps(record.metadata),
                        record.created_at,
                        record.data_timestamp,
                        record.project,
                    ),
                )
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise StorageError(f"Failed to save provenance record: {e}") from e

    def load_provenance_record(self, record_id: str) -> Optional[ProvenanceRecord]:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM provenance_records WHERE id = %s", (record_id,))
            row = cur.fetchone()
        if not row:
            return None
        return self._row_to_record(row, cur.description)

    def query_provenance_by_name(self, name: str, project: str = "default") -> list[ProvenanceRecord]:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM provenance_records WHERE name = %s AND project = %s ORDER BY created_at ASC",
                (name, project),
            )
            rows = cur.fetchall()
            desc = cur.description
        return [self._row_to_record(r, desc) for r in rows]

    def _row_to_record(self, row, description) -> ProvenanceRecord:
        cols = [d.name for d in description]
        d = dict(zip(cols, row))
        return ProvenanceRecord.from_dict({
            "id": d["id"],
            "name": d["name"],
            "source": d["source"],
            "parent_ids": d["parent_ids"] if isinstance(d["parent_ids"], list) else json.loads(d["parent_ids"] or "[]"),
            "fingerprint": d["fingerprint"],
            "row_count": d["row_count"],
            "column_count": d["column_count"],
            "column_names": d["column_names"] if isinstance(d["column_names"], list) else json.loads(d["column_names"] or "[]"),
            "byte_size": d["byte_size"],
            "statistical_summary": d["statistical_summary"] if isinstance(d["statistical_summary"], dict) else json.loads(d["statistical_summary"] or "{}"),
            "merkle_root": d["merkle_root"],
            "merkle_index": d["merkle_index"],
            "previous_root": d["previous_root"],
            "tags": d["tags"] if isinstance(d["tags"], list) else json.loads(d["tags"] or "[]"),
            "metadata": d["metadata"] if isinstance(d["metadata"], dict) else json.loads(d["metadata"] or "{}"),
            "created_at": d["created_at"].isoformat() if isinstance(d["created_at"], datetime) else d["created_at"],
            "data_timestamp": d["data_timestamp"].isoformat() if isinstance(d["data_timestamp"], datetime) else d.get("data_timestamp"),
            "project": d["project"],
        })

    # ── Merkle ────────────────────────────────────────────────

    def save_merkle_hash(self, index: int, hash_value: str, project: str = "default") -> None:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO merkle_nodes (idx, hash, project) VALUES (%s, %s, %s) ON CONFLICT (project, idx) DO UPDATE SET hash = EXCLUDED.hash",
                (index, hash_value, project),
            )
        conn.commit()

    def load_merkle_hashes(self, project: str = "default") -> list[str]:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT hash FROM merkle_nodes WHERE project = %s ORDER BY idx ASC", (project,))
            return [r[0] for r in cur.fetchall()]

    # ── Trust Scores ──────────────────────────────────────────

    def save_trust_score(self, score_data: dict) -> None:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO trust_scores
                   (id, record_id, dataset_name, composite, grade, dimensions,
                    warnings, computed_at, config_snapshot, project)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    score_data["id"], score_data.get("record_id"),
                    score_data.get("dataset_name"), score_data["composite"],
                    score_data["grade"], json.dumps(score_data["dimensions"]),
                    json.dumps(score_data.get("warnings", [])),
                    score_data["computed_at"],
                    json.dumps(score_data.get("config_snapshot", {})),
                    score_data.get("project", "default"),
                ),
            )
        conn.commit()

    def load_latest_trust_score(self, dataset_name: str, project: str = "default") -> Optional[dict]:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM trust_scores WHERE dataset_name = %s AND project = %s ORDER BY computed_at DESC LIMIT 1",
                (dataset_name, project),
            )
            row = cur.fetchone()
            if not row:
                return None
            cols = [d.name for d in cur.description]
            d = dict(zip(cols, row))
        return {
            "id": d["id"], "record_id": d["record_id"],
            "dataset_name": d["dataset_name"], "composite": d["composite"],
            "grade": d["grade"],
            "dimensions": d["dimensions"] if isinstance(d["dimensions"], list) else json.loads(d["dimensions"]),
            "warnings": d["warnings"] if isinstance(d["warnings"], list) else json.loads(d["warnings"] or "[]"),
            "computed_at": d["computed_at"].isoformat() if isinstance(d["computed_at"], datetime) else d["computed_at"],
        }

    # ── Compliance ────────────────────────────────────────────

    def save_compliance_report(self, report_data: dict) -> None:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO compliance_reports
                   (id, dataset_name, regulation, content, output_format,
                    generated_at, record_ids, trust_score_id, project)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    report_data["id"], report_data["dataset_name"],
                    report_data["regulation"], report_data["content"],
                    report_data["output_format"], report_data["generated_at"],
                    json.dumps(report_data.get("record_ids", [])),
                    report_data.get("trust_score_id"),
                    report_data.get("project", "default"),
                ),
            )
        conn.commit()

    # ── Stats ─────────────────────────────────────────────────

    def get_record_count(self, project: str = "default") -> int:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM provenance_records WHERE project = %s", (project,))
            return cur.fetchone()[0]

    def get_latest_records(self, project: str = "default", limit: int = 10) -> list[ProvenanceRecord]:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM provenance_records WHERE project = %s ORDER BY created_at DESC LIMIT %s",
                (project, limit),
            )
            rows = cur.fetchall()
            desc = cur.description
        return [self._row_to_record(r, desc) for r in rows]

    def close(self) -> None:
        if self._conn and not self._conn.closed:
            self._conn.close()
