"""TrustPipe error hierarchy."""

from __future__ import annotations


class TrustPipeError(Exception):
    """Base exception for all TrustPipe errors."""


class ConfigError(TrustPipeError):
    """Invalid or missing configuration."""


class StorageError(TrustPipeError):
    """Storage backend failure (read/write/migration)."""


class ProvenanceError(TrustPipeError):
    """Provenance chain integrity or recording failure."""


class VerificationError(ProvenanceError):
    """Merkle chain verification failed — possible tamper."""


class ScoringError(TrustPipeError):
    """Trust score computation failure."""


class ComplianceError(TrustPipeError):
    """Compliance report generation failure."""


class PluginError(TrustPipeError):
    """Plugin activation or lifecycle failure."""
