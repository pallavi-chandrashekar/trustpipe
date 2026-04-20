"""Tests for multi-project federation."""

import pytest

from trustpipe import TrustPipe
from trustpipe.core.federation import Federation


@pytest.fixture
def federated(tmp_path):
    """Create 3 federated TrustPipe instances."""
    prod = TrustPipe(project="production", db_path=tmp_path / "prod.db")
    staging = TrustPipe(project="staging", db_path=tmp_path / "staging.db")
    ml = TrustPipe(project="ml", db_path=tmp_path / "ml.db")

    # Seed data in each
    prod.track({"rows": 10000}, name="customers", source="s3://prod/customers")
    prod.track({"rows": 5000}, name="orders", source="s3://prod/orders")

    staging.track({"rows": 8000}, name="customers", source="s3://staging/customers")
    staging.track({"rows": 3000}, name="events", source="s3://staging/events")

    ml.track({"rows": 7000}, name="training_set", source="pipeline://ml/features")
    ml.track({"rows": 7000}, name="customers", source="pipeline://ml/customers")

    return Federation([prod, staging, ml])


def test_federation_projects(federated):
    assert federated.projects == ["production", "staging", "ml"]


def test_federation_status(federated):
    status = federated.status()
    assert len(status.projects) == 3
    assert status.total_records == 6  # 2 + 2 + 2
    assert status.all_healthy is True


def test_federation_search_across_projects(federated):
    """'customers' exists in all 3 projects."""
    results = federated.search("customers")
    assert len(results) == 3
    projects = {r.project for r in results}
    assert projects == {"production", "staging", "ml"}


def test_federation_search_single_project(federated):
    """'training_set' only exists in ml."""
    results = federated.search("training_set")
    assert len(results) == 1
    assert results[0].project == "ml"


def test_federation_search_not_found(federated):
    results = federated.search("nonexistent")
    assert results == []


def test_federation_trace(federated):
    traces = federated.trace("customers")
    assert len(traces) == 3
    assert "production" in traces
    assert "staging" in traces
    assert "ml" in traces


def test_federation_verify_all(federated):
    results = federated.verify_all()
    assert len(results) == 3
    assert all(r["integrity"] == "OK" for r in results.values())


def test_federation_get_all_datasets(federated):
    datasets = federated.get_all_datasets()
    assert "production" in datasets
    assert "customers" in datasets["production"]
    assert "orders" in datasets["production"]
    assert "training_set" in datasets["ml"]
