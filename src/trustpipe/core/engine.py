"""TrustPipe — main entry point. Orchestrates provenance, trust, and compliance."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Union

from trustpipe.core.config import TrustPipeConfig
from trustpipe.core.exceptions import ProvenanceError
from trustpipe.provenance.chain import ProvenanceChain
from trustpipe.provenance.lineage import LineageGraph
from trustpipe.provenance.record import ProvenanceRecord, fingerprint_data
from trustpipe.storage.base import StorageBackend
from trustpipe.storage.sqlite import SQLiteBackend


class TrustPipe:
    """Main entry point. Orchestrates provenance, trust, and compliance.

    Zero-config constructor. Everything has sensible defaults.

    Usage (the 3-line promise):
        from trustpipe import TrustPipe
        tp = TrustPipe()
        tp.track(df, name="customers")
    """

    def __init__(
        self,
        *,
        config: Optional[TrustPipeConfig] = None,
        storage: Optional[StorageBackend] = None,
        project: str = "default",
        db_path: Optional[Union[str, Path]] = None,
    ) -> None:
        self._config = config or TrustPipeConfig.auto_detect()
        self._project = project
        self._storage = storage or SQLiteBackend(
            path=db_path or self._config.resolve_db_path(project)
        )
        self._storage.initialize()
        self._chain = ProvenanceChain(storage=self._storage, project=project)

    # ── Layer 1: Provenance ──────────────────────────────────

    def track(
        self,
        data: Any,
        *,
        name: str,
        source: Optional[str] = None,
        parent: Optional[str] = None,
        parents: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
        tags: Optional[list[str]] = None,
    ) -> ProvenanceRecord:
        """Record a data asset in the provenance chain.

        Args:
            data: The data object (DataFrame, path, or dict of stats).
                  TrustPipe fingerprints it (row count, column hash,
                  statistical summary) but NEVER stores the raw data.
            name: Human-readable identifier (e.g., "customer_features").
            source: Origin URI (s3://, gs://, jdbc://, file://, etc.).
            parent: Single parent record ID (for linear pipelines).
            parents: Multiple parent record IDs (for joins/unions).
            metadata: Arbitrary key-value pairs attached to the record.
            tags: Labels for categorization (e.g., ["pii", "training"]).

        Returns:
            ProvenanceRecord with assigned ID, Merkle root, and timestamp.
        """
        if not name:
            raise ProvenanceError("name is required for track()")

        # Build parent list
        parent_ids: list[str] = []
        if parent:
            parent_ids.append(parent)
        if parents:
            parent_ids.extend(parents)

        # Fingerprint the data
        fp = fingerprint_data(data)

        record = ProvenanceRecord(
            name=name,
            source=source,
            parent_ids=parent_ids,
            fingerprint=fp.get("fingerprint", ""),
            row_count=fp.get("row_count"),
            column_count=fp.get("column_count"),
            column_names=fp.get("column_names", []),
            byte_size=fp.get("byte_size"),
            statistical_summary=fp.get("statistical_summary", {}),
            tags=tags or [],
            metadata=metadata or {},
            project=self._project,
        )

        return self._chain.append(record)

    def trace(self, name: str) -> list[ProvenanceRecord]:
        """Return full provenance chain for a named dataset, root to leaf."""
        return self._chain.get_chain(name)

    def lineage(self, name: str) -> Optional[LineageGraph]:
        """Return the lineage DAG for the latest version of a named dataset."""
        chain = self._chain.get_chain(name)
        if not chain:
            return None
        latest = chain[-1]
        return LineageGraph.build(latest.id, self._storage)

    def verify(self, record_id: Optional[str] = None) -> dict[str, Any]:
        """Verify Merkle chain integrity.

        If record_id is given, verify that specific record.
        Otherwise, verify all records.
        """
        if record_id:
            ok = self._chain.verify(record_id)
            return {"record_id": record_id, "verified": ok}

        total = self._chain.length
        verified = 0
        failed: list[str] = []

        records = self._storage.get_latest_records(self._project, limit=10000)
        for record in records:
            if self._chain.verify(record.id):
                verified += 1
            else:
                failed.append(record.id)

        return {
            "total": total,
            "verified": verified,
            "failed": len(failed),
            "failed_ids": failed,
            "chain_root": self._chain.root,
            "integrity": "OK" if not failed else "COMPROMISED",
        }

    # ── Properties ────────────────────────────────────────────

    @property
    def chain(self) -> ProvenanceChain:
        """Direct access to provenance chain for advanced queries."""
        return self._chain

    @property
    def config(self) -> TrustPipeConfig:
        return self._config

    @property
    def project(self) -> str:
        return self._project

    def status(self) -> dict[str, Any]:
        """Project summary: record count, chain health, latest records."""
        count = self._storage.get_record_count(self._project)
        latest = self._storage.get_latest_records(self._project, limit=5)
        return {
            "project": self._project,
            "record_count": count,
            "chain_length": self._chain.length,
            "chain_root": self._chain.root,
            "latest_records": [
                {"name": r.name, "source": r.source, "created_at": r.created_at.isoformat()}
                for r in latest
            ],
        }
