"""Six trust dimension calculators.

Each dimension computes a raw score from 0.0 (worst) to 1.0 (best).
Dimensions gracefully degrade when optional deps aren't installed.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from trustpipe.core.config import TrustPipeConfig
from trustpipe.provenance.record import ProvenanceRecord


@dataclass
class DimensionContext:
    """Context passed to each dimension calculator."""

    config: TrustPipeConfig
    provenance_record: ProvenanceRecord | None = None
    chain_length: int = 0
    data_timestamp: datetime | None = None
    created_at: datetime | None = None
    reference_data: Any = None
    previous_columns: list[str] | None = None
    previous_dtypes: dict[str, str] | None = None
    historical_row_count: int | None = None
    _stats_cache: dict[str, Any] | None = field(default=None, repr=False)

    def compute_stats(self, data: Any) -> dict[str, Any]:
        """Lazy-compute data statistics, cached."""
        if self._stats_cache is not None:
            return self._stats_cache

        stats: dict[str, Any] = {}
        try:
            import pandas as pd

            if isinstance(data, pd.DataFrame):
                stats["row_count"] = len(data)
                stats["column_names"] = list(data.columns)
                stats["dtypes"] = {col: str(dtype) for col, dtype in data.dtypes.items()}
                null_counts = data.isnull().sum()
                stats["null_ratio_mean"] = float(null_counts.mean() / max(len(data), 1))
                stats["null_ratios"] = {
                    col: float(null_counts[col] / max(len(data), 1)) for col in data.columns
                }
                self._stats_cache = stats
                return stats
        except ImportError:
            pass

        if isinstance(data, dict):
            stats = dict(data)

        self._stats_cache = stats
        return stats


class Dimension(ABC):
    """Base for individual trust dimension calculators."""

    name: str = ""

    @abstractmethod
    def compute(self, data: Any, context: DimensionContext) -> float:
        """Return raw score 0.0 (worst) to 1.0 (best)."""
        ...

    def explain(self, score: float, context: DimensionContext) -> dict[str, Any]:
        """Return details dict explaining the score."""
        return {"score": score}


class ProvenanceDepth(Dimension):
    """How well-documented is the data's origin?

    1.0: Full chain with Merkle verification + source + parents
    0.0: No provenance recorded
    """

    name = "Provenance Depth"

    def compute(self, data: Any, context: DimensionContext) -> float:
        record = context.provenance_record
        if record is None:
            return 0.0
        score = 0.2  # base: record exists
        if record.source:
            score += 0.3
        if record.parent_ids:
            score += 0.2
        if record.merkle_root and record.previous_root:
            score += 0.2
        if context.chain_length > 1:
            score += 0.1 * (1 - math.exp(-context.chain_length / 5))
        return min(score, 1.0)

    def explain(self, score: float, context: DimensionContext) -> dict[str, Any]:
        record = context.provenance_record
        return {
            "score": score,
            "has_source": bool(record and record.source),
            "has_parents": bool(record and record.parent_ids),
            "has_merkle": bool(record and record.merkle_root),
            "chain_length": context.chain_length,
        }


class Freshness(Dimension):
    """How recent is the data?

    Exponential decay: score = exp(-ln(2) * age_days / half_life).
    """

    name = "Freshness"

    def compute(self, data: Any, context: DimensionContext) -> float:
        timestamp = context.data_timestamp or context.created_at
        if timestamp is None:
            return 0.5  # unknown age -> neutral
        age_days = (datetime.now(timezone.utc) - timestamp).total_seconds() / 86400
        if age_days < 0:
            age_days = 0
        half_life = context.config.freshness_half_life_days
        return math.exp(-math.log(2) * age_days / half_life)

    def explain(self, score: float, context: DimensionContext) -> dict[str, Any]:
        timestamp = context.data_timestamp or context.created_at
        age_days = None
        if timestamp:
            age_days = round((datetime.now(timezone.utc) - timestamp).total_seconds() / 86400, 1)
        return {
            "score": score,
            "age_days": age_days,
            "half_life": context.config.freshness_half_life_days,
        }


class Completeness(Dimension):
    """What fraction of expected data is present?

    Measures null ratios and row count vs historical.
    """

    name = "Completeness"

    def compute(self, data: Any, context: DimensionContext) -> float:
        stats = context.compute_stats(data)
        null_ratio = stats.get("null_ratio_mean", 0.0)
        completeness = 1.0 - null_ratio

        if context.historical_row_count and stats.get("row_count"):
            ratio = stats["row_count"] / context.historical_row_count
            if ratio < 0.5:
                completeness *= 0.7
            elif ratio < 0.8:
                completeness *= 0.9

        return max(0.0, min(completeness, 1.0))

    def explain(self, score: float, context: DimensionContext) -> dict[str, Any]:
        stats = context.compute_stats(context) if hasattr(context, "compute_stats") else {}
        return {"score": score, "null_ratio_mean": stats.get("null_ratio_mean")}


class Consistency(Dimension):
    """Does the data conform to expected schema and value distributions?"""

    name = "Consistency"

    def compute(self, data: Any, context: DimensionContext) -> float:
        stats = context.compute_stats(data)
        score = 1.0

        if context.previous_columns:
            current = set(stats.get("column_names", []))
            expected = set(context.previous_columns)
            if current != expected:
                missing = expected - current
                extra = current - expected
                penalty = (len(missing) + len(extra) * 0.5) / max(len(expected), 1)
                score -= min(penalty, 0.5)

        if context.previous_dtypes:
            current_dtypes = stats.get("dtypes", {})
            for col, prev_dtype in context.previous_dtypes.items():
                if col in current_dtypes and current_dtypes[col] != prev_dtype:
                    score -= 0.1

        return max(0.0, min(score, 1.0))


class Drift(Dimension):
    """Has the data distribution shifted from the reference?

    Uses evidently if available, falls back to simple comparison.
    """

    name = "Drift"

    def compute(self, data: Any, context: DimensionContext) -> float:
        if context.reference_data is None:
            return 0.8  # no reference -> assume mostly OK but flag it

        try:
            from trustpipe.trust.drift import DriftDetector

            detector = DriftDetector(config=context.config)
            result = detector.detect(reference=context.reference_data, current=data)
            return 1.0 - result.drift_fraction
        except (ImportError, Exception):
            return self._simple_drift(data, context)

    def _simple_drift(self, data: Any, context: DimensionContext) -> float:
        """Fallback when evidently is not installed."""
        try:
            import pandas as pd

            if isinstance(data, pd.DataFrame) and isinstance(context.reference_data, pd.DataFrame):
                ref_means = context.reference_data.select_dtypes(include="number").mean()
                cur_means = data.select_dtypes(include="number").mean()
                common = ref_means.index.intersection(cur_means.index)
                if len(common) == 0:
                    return 0.7
                diffs = (
                    (cur_means[common] - ref_means[common]) / ref_means[common].clip(lower=1e-10)
                ).abs()
                drift_frac = (diffs > 0.2).mean()
                return max(0.0, 1.0 - float(drift_frac))
        except (ImportError, Exception):
            pass
        return 0.7


class PoisoningRisk(Dimension):
    """Likelihood the data has been tampered with or injected.

    Uses pyod if available, falls back to neutral score.
    """

    name = "Poisoning Risk"

    def compute(self, data: Any, context: DimensionContext) -> float:
        try:
            from trustpipe.trust.poisoning import PoisoningDetector

            detector = PoisoningDetector(config=context.config)
            result = detector.scan(data)
            threshold = context.config.poisoning_contamination
            anomaly_frac = result.anomaly_fraction
            if anomaly_frac <= threshold * 0.5:
                return 1.0
            elif anomaly_frac >= threshold * 2:
                return 0.0
            else:
                return 1.0 - (anomaly_frac / (threshold * 2))
        except (ImportError, Exception):
            return 0.7  # no pyod -> neutral


ALL_DIMENSION_CLASSES: list[type[Dimension]] = [
    ProvenanceDepth,
    Freshness,
    Completeness,
    Consistency,
    Drift,
    PoisoningRisk,
]
