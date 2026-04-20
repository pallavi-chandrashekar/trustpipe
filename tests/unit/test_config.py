"""Tests for configuration loading."""

from trustpipe.core.config import TrustPipeConfig


def test_default_config():
    config = TrustPipeConfig()
    assert config.storage_backend == "sqlite"
    assert config.project_name == "default"
    assert config.freshness_half_life_days == 30.0


def test_weights_sum_to_one():
    config = TrustPipeConfig()
    weights = config.get_weights()
    total = sum(weights.values())
    assert abs(total - 1.0) < 0.001


def test_env_var_override(monkeypatch):
    monkeypatch.setenv("TRUSTPIPE_STORAGE_BACKEND", "postgres")
    monkeypatch.setenv("TRUSTPIPE_FRESHNESS_HALF_LIFE_DAYS", "60.0")

    config = TrustPipeConfig._from_env()
    assert config.storage_backend == "postgres"
    assert config.freshness_half_life_days == 60.0


def test_resolve_db_path(tmp_path):
    config = TrustPipeConfig(storage_path=str(tmp_path / "custom.db"))
    path = config.resolve_db_path("myproject")
    assert str(path) == str(tmp_path / "custom.db")


def test_yaml_config(tmp_path):
    config_file = tmp_path / "trustpipe.yaml"
    config_file.write_text(
        """
storage:
  storage_backend: postgres
  storage_path: /tmp/test.db

scoring:
  freshness_half_life_days: 60.0
  poisoning_contamination: 0.1
"""
    )
    config = TrustPipeConfig._from_yaml(config_file)
    assert config.storage_backend == "postgres"
    assert config.freshness_half_life_days == 60.0
    assert config.poisoning_contamination == 0.1
