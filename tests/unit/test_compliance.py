"""Tests for compliance reporter and EU AI Act gap analysis."""

import pytest

from trustpipe.compliance.eu_ai_act import assess_compliance_gaps, build_article10_metadata
from trustpipe.compliance.schemas import Article10Metadata, BiasAssessment, ProcessDocumentation
from trustpipe.provenance.record import ProvenanceRecord


@pytest.fixture
def sample_records():
    return [
        ProvenanceRecord(
            id="rec1",
            name="raw_data",
            source="s3://bucket/raw.csv",
            fingerprint="fp1",
            merkle_root="root1",
            merkle_index=0,
            row_count=10000,
            column_count=5,
            column_names=["a", "b", "c", "d", "e"],
        ),
        ProvenanceRecord(
            id="rec2",
            name="clean_data",
            source="pipeline://etl/clean",
            fingerprint="fp2",
            merkle_root="root2",
            merkle_index=1,
            row_count=9500,
            parent_ids=["rec1"],
        ),
    ]


@pytest.fixture
def sample_trust_score():
    return {
        "composite": 85,
        "grade": "A",
        "dimensions": [
            {"name": "Completeness", "raw_score": 0.95},
            {"name": "Consistency", "raw_score": 0.90},
            {"name": "Freshness", "raw_score": 0.80},
        ],
    }


def test_build_metadata_from_records(sample_records, sample_trust_score):
    metadata = build_article10_metadata(
        records=sample_records,
        trust_score=sample_trust_score,
        verification_result={"integrity": "OK"},
    )
    assert metadata.provenance_records_count == 2
    assert metadata.merkle_chain_verified is True
    assert len(metadata.data_sources) == 2
    assert len(metadata.chain_of_custody) == 2
    assert metadata.trust_score == 85
    assert metadata.quality.completeness_score == 0.95


def test_build_metadata_with_user_fields(sample_records):
    metadata = build_article10_metadata(
        records=sample_records,
        user_metadata={
            "intended_use": "Customer churn prediction",
            "geographic_applicability": "United States",
        },
    )
    assert metadata.intended_use == "Customer churn prediction"
    assert metadata.geographic_applicability == "United States"


def test_gap_analysis_empty_metadata():
    metadata = Article10Metadata()
    gaps = assess_compliance_gaps(metadata)
    # Should find multiple critical gaps
    critical = [g for g in gaps if g.severity == "CRITICAL"]
    assert len(critical) >= 2  # at least: no sources, no bias methodology


def test_gap_analysis_identifies_missing_sources():
    metadata = Article10Metadata(data_sources=[])
    gaps = assess_compliance_gaps(metadata)
    source_gaps = [g for g in gaps if "data sources" in g.description.lower()]
    assert len(source_gaps) >= 1


def test_gap_analysis_identifies_missing_bias():
    metadata = Article10Metadata(
        data_sources=[{"uri": "s3://test"}],
        chain_of_custody=[{"record_id": "r1"}],
        merkle_chain_verified=True,
    )
    gaps = assess_compliance_gaps(metadata)
    bias_gaps = [g for g in gaps if "bias" in g.description.lower()]
    assert len(bias_gaps) >= 1


def test_gap_analysis_clean_metadata():
    """Well-documented metadata should have fewer gaps."""
    metadata = Article10Metadata(
        data_sources=[{"uri": "s3://test"}],
        chain_of_custody=[{"record_id": "r1"}],
        merkle_chain_verified=True,
        quality={"completeness_score": 0.95, "accuracy_assessment": "Cross-validated"},
        intended_use="ML model training for fraud detection",
        geographic_applicability="EU + US",
        bias=BiasAssessment(
            methodology="Disparate impact analysis",
            protected_attributes_checked=["gender", "age", "ethnicity"],
        ),
        process=ProcessDocumentation(
            governance_owner="Data Team Lead",
            preparation_methodology="Documented ETL pipeline",
        ),
    )
    gaps = assess_compliance_gaps(metadata)
    critical = [g for g in gaps if g.severity == "CRITICAL"]
    assert len(critical) == 0  # no critical gaps


def test_comply_generates_markdown(tp):
    """End-to-end: track data then generate compliance report."""
    tp.track({"rows": 1000}, name="test_data", source="s3://bucket/data.csv")
    tp.track({"rows": 950}, name="test_data", source="pipeline://clean", parent="")

    report = tp.comply("test_data", regulation="eu-ai-act-article-10")
    assert "Article 10" in report
    assert "test_data" in report
    assert "Data Sources" in report
    assert "Compliance Gap" in report


def test_comply_generates_datacard(tp):
    tp.track({"rows": 500}, name="card_data", source="db://prod")
    report = tp.comply("card_data", regulation="datacard")
    assert "Data Card" in report
    assert "card_data" in report


def test_comply_generates_audit_log(tp):
    tp.track({"rows": 500}, name="audit_data", source="s3://logs")
    report = tp.comply("audit_data", regulation="audit-log")
    assert "Audit Log" in report
    assert "audit_data" in report


def test_comply_json_format(tp):
    import json

    tp.track({"rows": 100}, name="json_test", source="file://test.csv")
    report = tp.comply("json_test", output_format="json")
    parsed = json.loads(report)
    assert "dataset_name" in parsed
    assert "metadata" in parsed
    assert "gaps" in parsed


def test_comply_with_trust_score(tp):
    """Compliance report should include trust score when available."""
    import pandas as pd

    df = pd.DataFrame({"a": range(100), "b": range(100)})
    tp.track(df, name="scored_data", source="s3://test")
    tp.score(df, name="scored_data")

    report = tp.comply("scored_data")
    assert "Trust Score" in report
