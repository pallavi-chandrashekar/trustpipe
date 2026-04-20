"""Default and configurable trust dimension weights."""

from __future__ import annotations

from trustpipe.core.config import TrustPipeConfig

# Dimension names (canonical)
PROVENANCE_DEPTH = "Provenance Depth"
FRESHNESS = "Freshness"
COMPLETENESS = "Completeness"
CONSISTENCY = "Consistency"
DRIFT = "Drift"
POISONING_RISK = "Poisoning Risk"

ALL_DIMENSIONS = [PROVENANCE_DEPTH, FRESHNESS, COMPLETENESS, CONSISTENCY, DRIFT, POISONING_RISK]

DEFAULT_WEIGHTS = {
    PROVENANCE_DEPTH: 0.15,
    FRESHNESS: 0.15,
    COMPLETENESS: 0.20,
    CONSISTENCY: 0.20,
    DRIFT: 0.15,
    POISONING_RISK: 0.15,
}


def get_weights(config: TrustPipeConfig | None = None) -> dict[str, float]:
    """Get dimension weights from config or defaults."""
    if config:
        return config.get_weights()
    return dict(DEFAULT_WEIGHTS)


def composite_to_grade(score: int) -> str:
    """Map composite score (0-100) to letter grade."""
    if score >= 95:
        return "A+"
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    if score >= 40:
        return "D"
    return "F"
