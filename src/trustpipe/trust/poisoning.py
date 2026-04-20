"""PoisoningDetector — dataset-level anomaly/poisoning detection with pyod fallback."""

from __future__ import annotations

from typing import Any

from trustpipe.core.config import TrustPipeConfig
from trustpipe.trust.scorer import ScanResult


class PoisoningDetector:
    """Detects anomalous/poisoned records in a dataset.

    Uses PyOD (Isolation Forest) if available, falls back to
    simple statistical outlier detection via z-scores.
    """

    def __init__(self, config: TrustPipeConfig | None = None) -> None:
        self._config = config or TrustPipeConfig()

    def scan(self, data: Any, detectors: list[str] | None = None) -> ScanResult:
        """Scan data for anomalies/poisoning."""
        try:
            return self._scan_pyod(data, detectors)
        except ImportError:
            return self._scan_zscore(data)

    def _scan_pyod(self, data: Any, detectors: list[str] | None = None) -> ScanResult:
        """Use PyOD Isolation Forest for anomaly detection."""
        import numpy as np
        import pandas as pd
        from pyod.models.iforest import IForest

        if not isinstance(data, pd.DataFrame):
            raise TypeError("PyOD scan requires a pandas DataFrame")

        numeric = data.select_dtypes(include="number")
        if numeric.empty:
            return ScanResult(
                anomaly_fraction=0.0,
                flagged_count=0,
                total_count=len(data),
                detector_used="skipped (no numeric columns)",
            )

        # Fill NaN for the detector
        numeric_clean = numeric.fillna(numeric.median())

        contamination = self._config.poisoning_contamination
        model = IForest(contamination=contamination, random_state=42)
        model.fit(numeric_clean)

        labels = model.labels_  # 0 = normal, 1 = anomaly
        scores = model.decision_scores_
        flagged = int(np.sum(labels == 1))
        total = len(data)

        return ScanResult(
            anomaly_fraction=flagged / max(total, 1),
            flagged_count=flagged,
            total_count=total,
            detector_used="pyod (IsolationForest)",
            details={
                "contamination": contamination,
                "mean_anomaly_score": float(np.mean(scores)),
                "max_anomaly_score": float(np.max(scores)),
            },
        )

    def _scan_zscore(self, data: Any) -> ScanResult:
        """Fallback: simple z-score outlier detection."""
        try:
            import pandas as pd

            if not isinstance(data, pd.DataFrame):
                return ScanResult(
                    anomaly_fraction=0.0,
                    flagged_count=0,
                    total_count=0,
                    detector_used="skipped (not DataFrame)",
                )

            numeric = data.select_dtypes(include="number")
            if numeric.empty:
                return ScanResult(
                    anomaly_fraction=0.0,
                    flagged_count=0,
                    total_count=len(data),
                    detector_used="skipped (no numeric columns)",
                )

            means = numeric.mean()
            stds = numeric.std().clip(lower=1e-10)
            z_scores = ((numeric - means) / stds).abs()

            # Flag rows where any column has z-score > 3
            flagged_mask = (z_scores > 3).any(axis=1)
            flagged = int(flagged_mask.sum())
            total = len(data)

            return ScanResult(
                anomaly_fraction=flagged / max(total, 1),
                flagged_count=flagged,
                total_count=total,
                detector_used="zscore (fallback, |z| > 3)",
                details={
                    "threshold": 3.0,
                    "columns_checked": list(numeric.columns),
                },
            )

        except ImportError:
            return ScanResult(
                anomaly_fraction=0.0,
                flagged_count=0,
                total_count=0,
                detector_used="skipped (pandas not available)",
            )
