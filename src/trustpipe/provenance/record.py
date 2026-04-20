"""ProvenanceRecord — immutable record of a data asset's provenance."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ProvenanceRecord:
    """Immutable record of a data asset in the provenance chain.

    TrustPipe fingerprints the data (row count, column hash, statistical
    summary) but NEVER stores the raw data itself.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    source: str | None = None
    parent_ids: list[str] = field(default_factory=list)

    # Fingerprint (computed from data, never stores raw data)
    fingerprint: str = ""
    row_count: int | None = None
    column_count: int | None = None
    column_names: list[str] = field(default_factory=list)
    byte_size: int | None = None
    statistical_summary: dict[str, Any] = field(default_factory=dict)

    # Merkle chain
    merkle_root: str = ""
    merkle_index: int = 0
    previous_root: str = ""

    # Metadata
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    data_timestamp: datetime | None = None

    # Project namespace
    project: str = "default"

    def content_hash(self) -> str:
        """Deterministic hash of the record's content for Merkle leaf."""
        payload = json.dumps(
            {
                "id": self.id,
                "name": self.name,
                "source": self.source,
                "fingerprint": self.fingerprint,
                "parent_ids": sorted(self.parent_ids),
                "row_count": self.row_count,
                "column_names": sorted(self.column_names),
                "created_at": self.created_at.isoformat(),
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        """Serializable representation for storage."""
        return {
            "id": self.id,
            "name": self.name,
            "source": self.source,
            "parent_ids": self.parent_ids,
            "fingerprint": self.fingerprint,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "column_names": self.column_names,
            "byte_size": self.byte_size,
            "statistical_summary": self.statistical_summary,
            "merkle_root": self.merkle_root,
            "merkle_index": self.merkle_index,
            "previous_root": self.previous_root,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "data_timestamp": self.data_timestamp.isoformat() if self.data_timestamp else None,
            "project": self.project,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProvenanceRecord:
        """Reconstruct from stored dict."""
        created_at = data.get("created_at", "")
        if isinstance(created_at, str) and created_at:
            created_at = datetime.fromisoformat(created_at)
        else:
            created_at = datetime.now(timezone.utc)

        data_ts = data.get("data_timestamp")
        data_ts = datetime.fromisoformat(data_ts) if isinstance(data_ts, str) and data_ts else None

        return cls(
            id=data.get("id", uuid.uuid4().hex[:12]),
            name=data.get("name", ""),
            source=data.get("source"),
            parent_ids=data.get("parent_ids", []),
            fingerprint=data.get("fingerprint", ""),
            row_count=data.get("row_count"),
            column_count=data.get("column_count"),
            column_names=data.get("column_names", []),
            byte_size=data.get("byte_size"),
            statistical_summary=data.get("statistical_summary", {}),
            merkle_root=data.get("merkle_root", ""),
            merkle_index=data.get("merkle_index", 0),
            previous_root=data.get("previous_root", ""),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            created_at=created_at,
            data_timestamp=data_ts,
            project=data.get("project", "default"),
        )


def fingerprint_data(data: Any) -> dict[str, Any]:
    """Extract a fingerprint from a data object without storing raw data.

    Supports: pandas DataFrame, dict of stats, file path, or raw string.
    Returns dict with fingerprint hash, row_count, column_names, etc.
    """
    result: dict[str, Any] = {}

    # pandas DataFrame
    try:
        import pandas as pd

        if isinstance(data, pd.DataFrame):
            result["row_count"] = len(data)
            result["column_count"] = len(data.columns)
            result["column_names"] = list(data.columns)
            result["byte_size"] = data.memory_usage(deep=True).sum()

            # Statistical summary (null ratios, dtypes)
            summary: dict[str, Any] = {}
            null_counts = data.isnull().sum()
            summary["null_ratio_mean"] = float(null_counts.mean() / max(len(data), 1))
            summary["dtypes"] = {col: str(dtype) for col, dtype in data.dtypes.items()}
            result["statistical_summary"] = summary

            # Fingerprint: hash of shape + column names + first/last row hashes
            content = f"{data.shape}|{'|'.join(data.columns)}|{data.dtypes.to_dict()}"
            result["fingerprint"] = hashlib.sha256(content.encode()).hexdigest()
            return result
    except ImportError:
        pass

    # Dict of pre-computed stats
    if isinstance(data, dict):
        result["row_count"] = data.get("rows", data.get("row_count"))
        result["column_count"] = data.get("columns", data.get("column_count"))
        result["column_names"] = data.get("column_names", [])
        result["statistical_summary"] = {
            k: v
            for k, v in data.items()
            if k not in ("rows", "columns", "column_names", "row_count", "column_count")
        }
        content = json.dumps(data, sort_keys=True, default=str)
        result["fingerprint"] = hashlib.sha256(content.encode()).hexdigest()
        return result

    # Fallback: hash the string representation
    content = str(data)
    result["fingerprint"] = hashlib.sha256(content.encode()).hexdigest()
    return result
