"""TrustScorer — compute 0-100 composite trust score."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from trustpipe.core.config import TrustPipeConfig
from trustpipe.provenance.record import ProvenanceRecord
from trustpipe.trust.dimensions import (
    ALL_DIMENSION_CLASSES,
    Dimension,
    DimensionContext,
)
from trustpipe.trust.weights import composite_to_grade, get_weights


@dataclass(frozen=True)
class DimensionScore:
    """Score for a single trust dimension."""

    name: str
    raw_score: float
    weighted_score: float
    weight: float
    grade: str = ""
    details: dict = field(default_factory=dict)


@dataclass(frozen=True)
class TrustScore:
    """Composite trust score for a data asset."""

    composite: int  # 0-100
    grade: str  # A+ / A / B / C / D / F
    dimensions: list[DimensionScore]
    record_id: str | None = None
    dataset_name: str | None = None
    warnings: list[str] = field(default_factory=list)
    computed_at: str = ""
    id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "composite": self.composite,
            "grade": self.grade,
            "dataset_name": self.dataset_name,
            "record_id": self.record_id,
            "dimensions": [
                {
                    "name": d.name,
                    "raw_score": round(d.raw_score, 4),
                    "weighted_score": round(d.weighted_score, 4),
                    "weight": d.weight,
                    "grade": d.grade,
                    "details": d.details,
                }
                for d in self.dimensions
            ],
            "warnings": self.warnings,
            "computed_at": self.computed_at,
        }

    def explain(self) -> str:
        """Human-readable explanation of the score."""
        lines = [f"Trust Score: {self.composite}/100 (Grade: {self.grade})"]
        lines.append("")
        for d in sorted(self.dimensions, key=lambda x: -x.raw_score):
            bar_len = int(d.raw_score * 20)
            bar = "\u2588" * bar_len + "\u2591" * (20 - bar_len)
            lines.append(f"  {d.name:<22} {bar} {d.raw_score * 100:5.1f} (w={d.weight:.2f})")
        if self.warnings:
            lines.append("")
            lines.append("Warnings:")
            for w in self.warnings:
                lines.append(f"  - {w}")
        return "\n".join(lines)


@dataclass
class ScanResult:
    """Result of a deep poisoning/anomaly scan."""

    anomaly_fraction: float
    flagged_count: int
    total_count: int
    detector_used: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "anomaly_fraction": round(self.anomaly_fraction, 4),
            "flagged_count": self.flagged_count,
            "total_count": self.total_count,
            "detector_used": self.detector_used,
            "details": self.details,
        }


class TrustScorer:
    """Computes trust scores from data + provenance context."""

    def __init__(self, config: TrustPipeConfig | None = None) -> None:
        self._config = config or TrustPipeConfig()
        self._dimensions: list[Dimension] = [cls() for cls in ALL_DIMENSION_CLASSES]

    def score(
        self,
        data: Any,
        *,
        name: str | None = None,
        provenance_record: ProvenanceRecord | None = None,
        chain_length: int = 0,
        reference: Any = None,
        previous_columns: list[str] | None = None,
        previous_dtypes: dict[str, str] | None = None,
        historical_row_count: int | None = None,
        checks: list[str] | None = None,
    ) -> TrustScore:
        """Compute composite trust score."""
        context = DimensionContext(
            config=self._config,
            provenance_record=provenance_record,
            chain_length=chain_length,
            data_timestamp=provenance_record.data_timestamp if provenance_record else None,
            created_at=provenance_record.created_at if provenance_record else None,
            reference_data=reference,
            previous_columns=previous_columns,
            previous_dtypes=previous_dtypes,
            historical_row_count=historical_row_count,
        )

        weights = get_weights(self._config)
        dimension_scores: list[DimensionScore] = []
        warnings: list[str] = []
        total_weighted = 0.0
        total_weight = 0.0

        for dim in self._dimensions:
            if checks and dim.name not in checks:
                continue

            weight = weights.get(dim.name, 1 / 6)
            try:
                raw = dim.compute(data, context)
            except Exception as e:
                raw = 0.5
                warnings.append(f"{dim.name}: computation failed ({e})")

            raw = max(0.0, min(1.0, raw))
            weighted = raw * weight
            total_weighted += weighted
            total_weight += weight

            ds = DimensionScore(
                name=dim.name,
                raw_score=raw,
                weighted_score=weighted,
                weight=weight,
                grade=composite_to_grade(round(raw * 100)),
                details=dim.explain(raw, context),
            )
            dimension_scores.append(ds)

            # Generate warnings for low scores
            if raw < 0.4:
                warnings.append(f"{dim.name}: score is critically low ({raw:.2f})")
            elif raw < 0.6:
                warnings.append(f"{dim.name}: below acceptable threshold ({raw:.2f})")

        composite = round((total_weighted / total_weight) * 100) if total_weight > 0 else 0
        grade = composite_to_grade(composite)

        return TrustScore(
            id=uuid.uuid4().hex[:12],
            composite=composite,
            grade=grade,
            dimensions=dimension_scores,
            record_id=provenance_record.id if provenance_record else None,
            dataset_name=name,
            warnings=warnings,
            computed_at=datetime.now(timezone.utc).isoformat(),
        )
