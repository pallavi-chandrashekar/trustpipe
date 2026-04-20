"""EU AI Act Article 10 compliance assessment and gap analysis."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from trustpipe.compliance.schemas import (
    Article10Metadata,
    ComplianceGap,
    DataSourceInfo,
    QualityMetrics,
)
from trustpipe.provenance.record import ProvenanceRecord


def build_article10_metadata(
    records: list[ProvenanceRecord],
    trust_score: Optional[dict] = None,
    verification_result: Optional[dict] = None,
    user_metadata: Optional[dict[str, Any]] = None,
) -> Article10Metadata:
    """Build Article 10 metadata from provenance records and trust scores.

    Automatically populates what can be derived from TrustPipe data.
    User-supplied metadata fills in fields that require human input
    (intended use, bias methodology, governance owner, etc.).
    """
    user_meta = user_metadata or {}

    # Data sources from provenance
    sources: list[DataSourceInfo] = []
    seen_sources: set[str] = set()
    for r in records:
        if r.source and r.source not in seen_sources:
            seen_sources.add(r.source)
            sources.append(DataSourceInfo(
                uri=r.source,
                description=r.metadata.get("description", ""),
                collection_method=r.metadata.get("collection_method", ""),
                geographic_origin=r.metadata.get("geographic_origin", ""),
                owner=r.metadata.get("owner", ""),
            ))

    # Chain of custody from provenance records
    chain = [
        {
            "record_id": r.id,
            "name": r.name,
            "source": r.source,
            "timestamp": r.created_at.isoformat(),
            "row_count": r.row_count,
            "fingerprint": r.fingerprint[:16] + "..." if r.fingerprint else "",
            "merkle_verified": bool(r.merkle_root),
        }
        for r in records
    ]

    # Quality metrics from trust score
    quality = QualityMetrics()
    if trust_score:
        dims = {d["name"]: d["raw_score"] for d in trust_score.get("dimensions", [])}
        quality.completeness_score = dims.get("Completeness", 0.0)
        quality.consistency_score = dims.get("Consistency", 0.0)
        quality.freshness_score = dims.get("Freshness", 0.0)
    if records:
        latest = records[-1]
        quality.row_count = latest.row_count
        quality.column_count = latest.column_count

    # Merkle verification
    merkle_verified = False
    if verification_result:
        merkle_verified = verification_result.get("integrity") == "OK"

    metadata = Article10Metadata(
        data_sources=sources,
        chain_of_custody=chain,
        provenance_records_count=len(records),
        merkle_chain_verified=merkle_verified,
        quality=quality,
        trust_score=trust_score.get("composite") if trust_score else None,
        trust_grade=trust_score.get("grade", "") if trust_score else "",
        assessment_date=datetime.now(timezone.utc).isoformat(),
        # User-supplied fields
        intended_use=user_meta.get("intended_use", ""),
        geographic_applicability=user_meta.get("geographic_applicability", ""),
        temporal_validity=user_meta.get("temporal_validity", ""),
        population_coverage=user_meta.get("population_coverage", ""),
        known_limitations=user_meta.get("known_limitations", []),
    )

    # Run gap analysis
    metadata.compliance_gaps = [g.description for g in assess_compliance_gaps(metadata)]

    return metadata


def assess_compliance_gaps(metadata: Article10Metadata) -> list[ComplianceGap]:
    """Identify which Article 10 requirements are not met."""
    gaps: list[ComplianceGap] = []

    # Art. 10(2)(a): Data sources and lineage
    if not metadata.data_sources:
        gaps.append(ComplianceGap(
            severity="CRITICAL",
            article_ref="Art. 10(2)(a)",
            description="No data sources documented",
            recommendation="Add source URIs when tracking data: tp.track(data, source='s3://...')",
        ))
    if not metadata.chain_of_custody:
        gaps.append(ComplianceGap(
            severity="CRITICAL",
            article_ref="Art. 10(2)(a)",
            description="No chain of custody / provenance lineage recorded",
            recommendation="Track all pipeline stages with parent linkage: tp.track(data, parent=prev.id)",
        ))
    if not metadata.merkle_chain_verified:
        gaps.append(ComplianceGap(
            severity="WARNING",
            article_ref="Art. 10(2)(a)",
            description="Merkle chain integrity not verified",
            recommendation="Run: trustpipe verify",
        ))

    # Art. 10(2)(b): Quality metrics
    if metadata.quality.completeness_score < 0.7:
        gaps.append(ComplianceGap(
            severity="WARNING",
            article_ref="Art. 10(2)(b)",
            description=f"Low data completeness ({metadata.quality.completeness_score:.0%})",
            recommendation="Investigate and reduce null values in the dataset",
        ))
    if not metadata.quality.accuracy_assessment:
        gaps.append(ComplianceGap(
            severity="WARNING",
            article_ref="Art. 10(2)(b)",
            description="No accuracy assessment methodology documented",
            recommendation="Document how data accuracy is measured and validated",
        ))

    # Art. 10(2)(c): Contextual appropriateness
    if not metadata.intended_use:
        gaps.append(ComplianceGap(
            severity="WARNING",
            article_ref="Art. 10(2)(c)",
            description="Intended use not documented",
            recommendation="Specify the AI system's intended purpose and deployment context",
        ))
    if not metadata.geographic_applicability:
        gaps.append(ComplianceGap(
            severity="INFO",
            article_ref="Art. 10(2)(c)",
            description="Geographic applicability not specified",
            recommendation="Document which regions/populations the data represents",
        ))

    # Art. 10(2)(f): Bias assessment
    if not metadata.bias.methodology:
        gaps.append(ComplianceGap(
            severity="CRITICAL",
            article_ref="Art. 10(2)(f)",
            description="No bias assessment methodology documented",
            recommendation="Document methods used to detect and mitigate bias in training data",
        ))
    if not metadata.bias.protected_attributes_checked:
        gaps.append(ComplianceGap(
            severity="WARNING",
            article_ref="Art. 10(2)(f)",
            description="No protected attributes checked for bias",
            recommendation="Identify and test protected attributes (gender, age, ethnicity, etc.)",
        ))

    # Art. 10(4): Data governance
    if not metadata.process.governance_owner:
        gaps.append(ComplianceGap(
            severity="WARNING",
            article_ref="Art. 10(4)",
            description="No data governance owner documented",
            recommendation="Assign a responsible person/team for data governance oversight",
        ))
    if not metadata.process.preparation_methodology:
        gaps.append(ComplianceGap(
            severity="INFO",
            article_ref="Art. 10(4)",
            description="Data preparation methodology not documented",
            recommendation="Document sampling, filtering, anonymization, and labeling procedures",
        ))

    return gaps
