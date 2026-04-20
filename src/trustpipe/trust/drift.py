"""DriftDetector — statistical drift detection with evidently fallback."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from trustpipe.core.config import TrustPipeConfig


@dataclass(frozen=True)
class DriftResult:
    """Result of drift detection between reference and current data."""

    drifted_columns: list[str]
    total_columns: int
    drift_fraction: float
    column_details: dict[str, dict] = field(default_factory=dict)
    test_method: str = "unknown"


class DriftDetector:
    """Wraps evidently for drift detection. Falls back to simple stats."""

    def __init__(self, config: TrustPipeConfig | None = None) -> None:
        self._config = config or TrustPipeConfig()

    def detect(self, reference: Any, current: Any) -> DriftResult:
        """Run drift detection between reference and current DataFrames."""
        try:
            return self._detect_evidently(reference, current)
        except ImportError:
            return self._detect_simple(reference, current)

    def _detect_evidently(self, reference: Any, current: Any) -> DriftResult:
        """Use evidently for comprehensive drift detection."""
        from evidently.metric_preset import DataDriftPreset
        from evidently.report import Report

        report = Report(metrics=[DataDriftPreset()])
        report.run(reference_data=reference, current_data=current)
        result_dict = report.as_dict()

        drift_info = result_dict["metrics"][0]["result"]
        drifted = [
            col for col, info in drift_info["drift_by_columns"].items() if info["drift_detected"]
        ]
        total = len(drift_info["drift_by_columns"])

        return DriftResult(
            drifted_columns=drifted,
            total_columns=total,
            drift_fraction=len(drifted) / max(total, 1),
            column_details=drift_info["drift_by_columns"],
            test_method="evidently (auto)",
        )

    def _detect_simple(self, reference: Any, current: Any) -> DriftResult:
        """Simple mean/std comparison when evidently is not installed."""
        try:
            import pandas as pd

            if not isinstance(reference, pd.DataFrame) or not isinstance(current, pd.DataFrame):
                return DriftResult(
                    drifted_columns=[],
                    total_columns=0,
                    drift_fraction=0.0,
                    test_method="skipped (not DataFrames)",
                )

            numeric_ref = reference.select_dtypes(include="number")
            numeric_cur = current.select_dtypes(include="number")
            common_cols = numeric_ref.columns.intersection(numeric_cur.columns)

            if len(common_cols) == 0:
                return DriftResult(
                    drifted_columns=[],
                    total_columns=0,
                    drift_fraction=0.0,
                    test_method="skipped (no common numeric columns)",
                )

            drifted: list[str] = []
            details: dict[str, dict] = {}

            for col in common_cols:
                ref_mean = numeric_ref[col].mean()
                cur_mean = numeric_cur[col].mean()
                ref_std = numeric_ref[col].std()

                # Drift if mean shifted by more than 2 std deviations
                threshold = max(abs(ref_std * 2), abs(ref_mean * 0.2), 1e-10)
                diff = abs(cur_mean - ref_mean)
                is_drifted = diff > threshold

                if is_drifted:
                    drifted.append(col)
                details[col] = {
                    "ref_mean": float(ref_mean),
                    "cur_mean": float(cur_mean),
                    "diff": float(diff),
                    "threshold": float(threshold),
                    "drift_detected": is_drifted,
                }

            total = len(common_cols)
            return DriftResult(
                drifted_columns=drifted,
                total_columns=total,
                drift_fraction=len(drifted) / max(total, 1),
                column_details=details,
                test_method="simple (mean/std comparison)",
            )

        except ImportError:
            return DriftResult(
                drifted_columns=[],
                total_columns=0,
                drift_fraction=0.0,
                test_method="skipped (pandas not available)",
            )
