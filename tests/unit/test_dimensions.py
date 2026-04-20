"""Tests for individual trust dimensions."""

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from trustpipe.core.config import TrustPipeConfig
from trustpipe.provenance.record import ProvenanceRecord
from trustpipe.trust.dimensions import (
    Completeness,
    Consistency,
    DimensionContext,
    Drift,
    Freshness,
    PoisoningRisk,
    ProvenanceDepth,
)


@pytest.fixture
def config():
    return TrustPipeConfig()


@pytest.fixture
def sample_df():
    return pd.DataFrame(
        {
            "id": range(100),
            "value": [float(i) for i in range(100)],
        }
    )


def test_provenance_depth_no_record(config):
    ctx = DimensionContext(config=config)
    dim = ProvenanceDepth()
    assert dim.compute(None, ctx) == 0.0


def test_provenance_depth_full_record(config):
    record = ProvenanceRecord(
        name="test",
        source="s3://bucket/data",
        parent_ids=["p1"],
        merkle_root="root",
        previous_root="prev",
    )
    ctx = DimensionContext(config=config, provenance_record=record, chain_length=5)
    dim = ProvenanceDepth()
    score = dim.compute(None, ctx)
    assert score >= 0.8


def test_freshness_recent_data(config):
    now = datetime.now(timezone.utc)
    ctx = DimensionContext(config=config, created_at=now)
    dim = Freshness()
    score = dim.compute(None, ctx)
    assert score > 0.95  # just created


def test_freshness_old_data(config):
    old = datetime.now(timezone.utc) - timedelta(days=90)
    ctx = DimensionContext(config=config, created_at=old)
    dim = Freshness()
    score = dim.compute(None, ctx)
    assert score < 0.2  # 3x half-life


def test_freshness_unknown_age(config):
    ctx = DimensionContext(config=config)
    dim = Freshness()
    score = dim.compute(None, ctx)
    assert score == 0.5  # neutral


def test_completeness_no_nulls(config, sample_df):
    ctx = DimensionContext(config=config)
    dim = Completeness()
    score = dim.compute(sample_df, ctx)
    assert score >= 0.99


def test_completeness_with_nulls(config):
    df = pd.DataFrame(
        {
            "a": [1, None, 3, None, 5],
            "b": [None, None, None, None, None],
        }
    )
    ctx = DimensionContext(config=config)
    dim = Completeness()
    score = dim.compute(df, ctx)
    assert score < 0.7  # 60% null ratio


def test_consistency_no_schema_change(config, sample_df):
    ctx = DimensionContext(config=config)
    dim = Consistency()
    score = dim.compute(sample_df, ctx)
    assert score == 1.0  # no previous to compare


def test_consistency_with_schema_drift(config, sample_df):
    ctx = DimensionContext(
        config=config,
        previous_columns=["id", "value", "removed_col"],
    )
    dim = Consistency()
    score = dim.compute(sample_df, ctx)
    assert score < 1.0  # missing column


def test_drift_no_reference(config, sample_df):
    ctx = DimensionContext(config=config)
    dim = Drift()
    score = dim.compute(sample_df, ctx)
    assert score == 0.8  # no reference -> flagged neutral


def test_drift_with_same_reference(config, sample_df):
    ctx = DimensionContext(config=config, reference_data=sample_df)
    dim = Drift()
    score = dim.compute(sample_df, ctx)
    assert score >= 0.9  # same data -> no drift


def test_poisoning_risk_defaults_neutral(config, sample_df):
    ctx = DimensionContext(config=config)
    dim = PoisoningRisk()
    score = dim.compute(sample_df, ctx)
    # Should return something (either pyod result or fallback)
    assert 0.0 <= score <= 1.0
