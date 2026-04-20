"""Multi-project federation — cross-project lineage and unified views.

Usage:
    from trustpipe import TrustPipe
    from trustpipe.core.federation import Federation

    prod = TrustPipe(project="production", db_path="prod.db")
    staging = TrustPipe(project="staging", db_path="staging.db")
    ml = TrustPipe(project="ml-training", db_path="ml.db")

    fed = Federation([prod, staging, ml])

    # Unified status across all projects
    status = fed.status()

    # Search for a dataset across all projects
    results = fed.search("customer_features")

    # Cross-project lineage
    lineage = fed.trace("customer_features")

    # Unified verify
    health = fed.verify_all()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from trustpipe.core.engine import TrustPipe
from trustpipe.provenance.record import ProvenanceRecord


@dataclass
class FederatedSearchResult:
    """Search result from a federated query."""

    project: str
    records: list[ProvenanceRecord]
    trust_score: Optional[dict] = None


@dataclass
class FederatedStatus:
    """Unified status across all projects."""

    projects: list[dict[str, Any]]
    total_records: int = 0
    total_chain_length: int = 0
    all_healthy: bool = True


class Federation:
    """Federated view across multiple TrustPipe projects."""

    def __init__(self, instances: list[TrustPipe]) -> None:
        self._instances = instances

    @property
    def projects(self) -> list[str]:
        return [tp.project for tp in self._instances]

    def status(self) -> FederatedStatus:
        """Unified status across all projects."""
        project_statuses = []
        total_records = 0
        total_chain = 0
        all_healthy = True

        for tp in self._instances:
            s = tp.status()
            v = tp.verify()
            project_statuses.append({
                "project": tp.project,
                "record_count": s["record_count"],
                "chain_length": s["chain_length"],
                "chain_root": s["chain_root"],
                "integrity": v["integrity"],
            })
            total_records += s["record_count"]
            total_chain += s["chain_length"]
            if v["integrity"] != "OK":
                all_healthy = False

        return FederatedStatus(
            projects=project_statuses,
            total_records=total_records,
            total_chain_length=total_chain,
            all_healthy=all_healthy,
        )

    def search(self, name: str) -> list[FederatedSearchResult]:
        """Search for a dataset name across all projects."""
        results = []
        for tp in self._instances:
            chain = tp.trace(name)
            if chain:
                score_data = tp._storage.load_latest_trust_score(name, tp.project)
                results.append(FederatedSearchResult(
                    project=tp.project,
                    records=chain,
                    trust_score=score_data,
                ))
        return results

    def trace(self, name: str) -> dict[str, list[ProvenanceRecord]]:
        """Trace a dataset across all projects. Returns project -> records mapping."""
        traces = {}
        for tp in self._instances:
            chain = tp.trace(name)
            if chain:
                traces[tp.project] = chain
        return traces

    def verify_all(self) -> dict[str, dict[str, Any]]:
        """Verify chain integrity across all projects."""
        results = {}
        for tp in self._instances:
            results[tp.project] = tp.verify()
        return results

    def score_all(self, name: str) -> dict[str, Optional[dict]]:
        """Get latest trust score for a dataset across all projects."""
        scores = {}
        for tp in self._instances:
            score = tp._storage.load_latest_trust_score(name, tp.project)
            if score:
                scores[tp.project] = score
        return scores

    def get_all_datasets(self) -> dict[str, list[str]]:
        """List all unique dataset names per project."""
        datasets: dict[str, list[str]] = {}
        for tp in self._instances:
            records = tp._storage.get_latest_records(tp.project, limit=10000)
            names = list(dict.fromkeys(r.name for r in records))
            datasets[tp.project] = names
        return datasets
