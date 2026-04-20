"""Abstract storage backend interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trustpipe.provenance.record import ProvenanceRecord


class StorageBackend(ABC):
    """Abstract storage interface. All backends implement this contract.

    The storage layer is a dumb persistence layer. It does not compute
    anything. It stores and retrieves records. Business logic lives in
    ProvenanceChain, TrustScorer, and ComplianceReporter.
    """

    @abstractmethod
    def initialize(self) -> None:
        """Create tables/collections if they don't exist. Run migrations."""
        ...

    # ── Provenance ────────────────────────────────────────────

    @abstractmethod
    def save_provenance_record(self, record: ProvenanceRecord) -> None: ...

    @abstractmethod
    def load_provenance_record(self, record_id: str) -> ProvenanceRecord | None: ...

    @abstractmethod
    def query_provenance_by_name(
        self, name: str, project: str = "default"
    ) -> list[ProvenanceRecord]:
        """Return all records for a name, ordered by created_at ASC."""
        ...

    # ── Merkle ────────────────────────────────────────────────

    @abstractmethod
    def save_merkle_hash(self, index: int, hash_value: str, project: str = "default") -> None: ...

    @abstractmethod
    def load_merkle_hashes(self, project: str = "default") -> list[str]:
        """Return all Merkle leaf hashes in index order."""
        ...

    # ── Trust Scores ──────────────────────────────────────────

    @abstractmethod
    def save_trust_score(self, score_data: dict) -> None: ...

    @abstractmethod
    def load_latest_trust_score(
        self, dataset_name: str, project: str = "default"
    ) -> dict | None: ...

    # ── Compliance ────────────────────────────────────────────

    @abstractmethod
    def save_compliance_report(self, report_data: dict) -> None: ...

    # ── Stats ─────────────────────────────────────────────────

    @abstractmethod
    def get_record_count(self, project: str = "default") -> int: ...

    @abstractmethod
    def get_latest_records(
        self, project: str = "default", limit: int = 10
    ) -> list[ProvenanceRecord]: ...
