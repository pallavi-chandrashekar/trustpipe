"""SQLite storage backend — zero-config default."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from trustpipe.core.exceptions import StorageError
from trustpipe.provenance.record import ProvenanceRecord
from trustpipe.storage.base import StorageBackend
from trustpipe.storage.migrations.v001_initial import SCHEMA_VERSION as V1_VERSION
from trustpipe.storage.migrations.v001_initial import SQL as V1_SQL


class SQLiteBackend(StorageBackend):
    """SQLite storage. Default backend — requires no external services."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
        self._conn: Optional[sqlite3.Connection] = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self._path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def initialize(self) -> None:
        conn = self._get_conn()
        current_version = self._get_schema_version(conn)
        if current_version < V1_VERSION:
            try:
                conn.executescript(V1_SQL)
                conn.execute(
                    "INSERT OR REPLACE INTO schema_version (version, applied_at) VALUES (?, ?)",
                    (V1_VERSION, datetime.now(timezone.utc).isoformat()),
                )
                conn.commit()
            except sqlite3.Error as e:
                raise StorageError(f"Migration v001 failed: {e}") from e

    def _get_schema_version(self, conn: sqlite3.Connection) -> int:
        try:
            row = conn.execute(
                "SELECT MAX(version) FROM schema_version"
            ).fetchone()
            return row[0] if row and row[0] else 0
        except sqlite3.OperationalError:
            return 0

    # ── Provenance ────────────────────────────────────────────

    def save_provenance_record(self, record: ProvenanceRecord) -> None:
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO provenance_records
                   (id, name, source, parent_ids, fingerprint, row_count,
                    column_count, column_names, byte_size, statistical_summary,
                    merkle_root, merkle_index, previous_root, tags, metadata,
                    created_at, data_timestamp, project)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    record.id,
                    record.name,
                    record.source,
                    json.dumps(record.parent_ids),
                    record.fingerprint,
                    record.row_count,
                    record.column_count,
                    json.dumps(record.column_names),
                    record.byte_size,
                    json.dumps(record.statistical_summary),
                    record.merkle_root,
                    record.merkle_index,
                    record.previous_root,
                    json.dumps(record.tags),
                    json.dumps(record.metadata),
                    record.created_at.isoformat(),
                    record.data_timestamp.isoformat() if record.data_timestamp else None,
                    record.project,
                ),
            )
            conn.commit()
        except sqlite3.Error as e:
            raise StorageError(f"Failed to save provenance record: {e}") from e

    def load_provenance_record(self, record_id: str) -> Optional[ProvenanceRecord]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM provenance_records WHERE id = ?", (record_id,)
        ).fetchone()
        if not row:
            return None
        return self._row_to_record(row)

    def query_provenance_by_name(
        self, name: str, project: str = "default"
    ) -> list[ProvenanceRecord]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM provenance_records WHERE name = ? AND project = ? ORDER BY created_at ASC",
            (name, project),
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def _row_to_record(self, row: sqlite3.Row) -> ProvenanceRecord:
        return ProvenanceRecord.from_dict({
            "id": row["id"],
            "name": row["name"],
            "source": row["source"],
            "parent_ids": json.loads(row["parent_ids"] or "[]"),
            "fingerprint": row["fingerprint"],
            "row_count": row["row_count"],
            "column_count": row["column_count"],
            "column_names": json.loads(row["column_names"] or "[]"),
            "byte_size": row["byte_size"],
            "statistical_summary": json.loads(row["statistical_summary"] or "{}"),
            "merkle_root": row["merkle_root"],
            "merkle_index": row["merkle_index"],
            "previous_root": row["previous_root"],
            "tags": json.loads(row["tags"] or "[]"),
            "metadata": json.loads(row["metadata"] or "{}"),
            "created_at": row["created_at"],
            "data_timestamp": row["data_timestamp"],
            "project": row["project"],
        })

    # ── Merkle ────────────────────────────────────────────────

    def save_merkle_hash(self, index: int, hash_value: str, project: str = "default") -> None:
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO merkle_nodes (idx, hash, project) VALUES (?, ?, ?)",
            (index, hash_value, project),
        )
        conn.commit()

    def load_merkle_hashes(self, project: str = "default") -> list[str]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT hash FROM merkle_nodes WHERE project = ? ORDER BY idx ASC",
            (project,),
        ).fetchall()
        return [r["hash"] for r in rows]

    # ── Trust Scores ──────────────────────────────────────────

    def save_trust_score(self, score_data: dict) -> None:
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO trust_scores
               (id, record_id, dataset_name, composite, grade, dimensions,
                warnings, computed_at, config_snapshot, project)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                score_data["id"],
                score_data.get("record_id"),
                score_data.get("dataset_name"),
                score_data["composite"],
                score_data["grade"],
                json.dumps(score_data["dimensions"]),
                json.dumps(score_data.get("warnings", [])),
                score_data["computed_at"],
                json.dumps(score_data.get("config_snapshot", {})),
                score_data.get("project", "default"),
            ),
        )
        conn.commit()

    def load_latest_trust_score(
        self, dataset_name: str, project: str = "default"
    ) -> Optional[dict]:
        conn = self._get_conn()
        row = conn.execute(
            """SELECT * FROM trust_scores
               WHERE dataset_name = ? AND project = ?
               ORDER BY computed_at DESC LIMIT 1""",
            (dataset_name, project),
        ).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "record_id": row["record_id"],
            "dataset_name": row["dataset_name"],
            "composite": row["composite"],
            "grade": row["grade"],
            "dimensions": json.loads(row["dimensions"]),
            "warnings": json.loads(row["warnings"] or "[]"),
            "computed_at": row["computed_at"],
        }

    # ── Compliance ────────────────────────────────────────────

    def save_compliance_report(self, report_data: dict) -> None:
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO compliance_reports
               (id, dataset_name, regulation, content, output_format,
                generated_at, record_ids, trust_score_id, project)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                report_data["id"],
                report_data["dataset_name"],
                report_data["regulation"],
                report_data["content"],
                report_data["output_format"],
                report_data["generated_at"],
                json.dumps(report_data.get("record_ids", [])),
                report_data.get("trust_score_id"),
                report_data.get("project", "default"),
            ),
        )
        conn.commit()

    # ── Stats ─────────────────────────────────────────────────

    def get_record_count(self, project: str = "default") -> int:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT COUNT(*) FROM provenance_records WHERE project = ?",
            (project,),
        ).fetchone()
        return row[0] if row else 0

    def get_latest_records(
        self, project: str = "default", limit: int = 10
    ) -> list[ProvenanceRecord]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM provenance_records WHERE project = ? ORDER BY created_at DESC LIMIT ?",
            (project, limit),
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
