"""Configuration loading: YAML file → env vars → defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Optional

from trustpipe.core.exceptions import ConfigError

DEFAULT_CONFIG_DIR = Path.home() / ".trustpipe"
CONFIG_SEARCH_ORDER = [
    Path("trustpipe.yaml"),
    Path("trustpipe.yml"),
    DEFAULT_CONFIG_DIR / "config.yaml",
    DEFAULT_CONFIG_DIR / "config.yml",
]


@dataclass(frozen=True)
class TrustPipeConfig:
    """Immutable configuration. Loaded once, never mutated at runtime."""

    # Storage
    storage_backend: str = "sqlite"
    storage_path: Optional[str] = None

    # Trust scoring weights (must sum to 1.0)
    weight_provenance_depth: float = 0.15
    weight_freshness: float = 0.15
    weight_completeness: float = 0.20
    weight_consistency: float = 0.20
    weight_drift: float = 0.15
    weight_poisoning_risk: float = 0.15

    # Thresholds
    drift_warning_threshold: float = 0.05
    drift_critical_threshold: float = 0.01
    poisoning_contamination: float = 0.05
    freshness_half_life_days: float = 30.0

    # LLM (optional)
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_api_key: Optional[str] = None

    # Project
    project_name: str = "default"

    @classmethod
    def auto_detect(cls) -> TrustPipeConfig:
        """Load config from first found YAML file, merge with env vars."""
        for path in CONFIG_SEARCH_ORDER:
            if path.exists():
                return cls._from_yaml(path)
        return cls._from_env()

    @classmethod
    def _from_yaml(cls, path: Path) -> TrustPipeConfig:
        try:
            import yaml
        except ImportError as e:
            raise ConfigError(f"PyYAML required to load config from {path}") from e

        raw = yaml.safe_load(path.read_text()) or {}
        flat: dict = {}
        for value in raw.values():
            if isinstance(value, dict):
                flat.update(value)
            # Also accept top-level keys
        flat.update({k: v for k, v in raw.items() if not isinstance(v, dict)})

        return cls._build(flat)

    @classmethod
    def _from_env(cls) -> TrustPipeConfig:
        return cls._build({})

    @classmethod
    def _build(cls, overrides: dict) -> TrustPipeConfig:
        """Build config from overrides dict + env vars."""
        field_names = {f.name for f in fields(cls)}
        kwargs: dict = {}

        for name in field_names:
            # Check env var first: TRUSTPIPE_STORAGE_BACKEND, etc.
            env_key = f"TRUSTPIPE_{name.upper()}"
            env_val = os.environ.get(env_key)
            if env_val is not None:
                kwargs[name] = _coerce(name, env_val, cls)
            elif name in overrides:
                kwargs[name] = overrides[name]

        return cls(**kwargs)

    def resolve_db_path(self, project: str) -> Path:
        if self.storage_path:
            return Path(self.storage_path)
        DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        return DEFAULT_CONFIG_DIR / f"{project}.db"

    def get_weights(self) -> dict[str, float]:
        return {
            "Provenance Depth": self.weight_provenance_depth,
            "Freshness": self.weight_freshness,
            "Completeness": self.weight_completeness,
            "Consistency": self.weight_consistency,
            "Drift": self.weight_drift,
            "Poisoning Risk": self.weight_poisoning_risk,
        }


def _coerce(field_name: str, value: str, cls: type) -> object:
    """Coerce a string env var to the field's type."""
    field_type = {f.name: f.type for f in fields(cls)}.get(field_name, "str")
    if "float" in str(field_type):
        return float(value)
    if "int" in str(field_type):
        return int(value)
    return value
