"""Tests for TrustScorer and TrustScore."""

import pandas as pd
import pytest

from trustpipe.trust.scorer import TrustScore, TrustScorer


@pytest.fixture
def scorer():
    return TrustScorer()


@pytest.fixture
def sample_df():
    return pd.DataFrame(
        {
            "id": range(1000),
            "value": [i * 1.1 for i in range(1000)],
            "category": ["A", "B", "C", "D"] * 250,
        }
    )


def test_score_returns_trust_score(scorer, sample_df):
    result = scorer.score(sample_df, name="test")
    assert isinstance(result, TrustScore)
    assert 0 <= result.composite <= 100
    assert result.grade in ("A+", "A", "B", "C", "D", "F")


def test_score_has_six_dimensions(scorer, sample_df):
    result = scorer.score(sample_df)
    assert len(result.dimensions) == 6


def test_score_dimensions_have_valid_ranges(scorer, sample_df):
    result = scorer.score(sample_df)
    for d in result.dimensions:
        assert 0.0 <= d.raw_score <= 1.0
        assert d.weight > 0


def test_score_with_subset_checks(scorer, sample_df):
    result = scorer.score(sample_df, checks=["Completeness", "Freshness"])
    assert len(result.dimensions) == 2
    names = {d.name for d in result.dimensions}
    assert names == {"Completeness", "Freshness"}


def test_score_explain_output(scorer, sample_df):
    result = scorer.score(sample_df)
    explanation = result.explain()
    assert "Trust Score:" in explanation
    assert "/100" in explanation


def test_score_to_dict(scorer, sample_df):
    result = scorer.score(sample_df, name="test")
    d = result.to_dict()
    assert "composite" in d
    assert "grade" in d
    assert "dimensions" in d
    assert isinstance(d["dimensions"], list)


def test_score_with_provenance_context(scorer, sample_df):
    from trustpipe.provenance.record import ProvenanceRecord

    record = ProvenanceRecord(
        name="test",
        source="s3://bucket/data.csv",
        fingerprint="abc",
        merkle_root="root",
        previous_root="prev",
        parent_ids=["parent1"],
    )
    result = scorer.score(sample_df, provenance_record=record, chain_length=3)
    # Provenance depth should be high with source + parents + merkle
    prov_dim = next(d for d in result.dimensions if d.name == "Provenance Depth")
    assert prov_dim.raw_score > 0.5


def test_dict_data_scores(scorer):
    result = scorer.score({"rows": 100, "columns": 5})
    assert 0 <= result.composite <= 100


def test_high_quality_data_scores_well(scorer):
    df = pd.DataFrame(
        {
            "a": range(10000),
            "b": [float(i) for i in range(10000)],
            "c": ["cat"] * 10000,
        }
    )
    result = scorer.score(df)
    # Complete data with no nulls should score well on completeness
    completeness = next(d for d in result.dimensions if d.name == "Completeness")
    assert completeness.raw_score >= 0.9
