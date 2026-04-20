"""Pydantic models for compliance metadata."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DataSourceInfo(BaseModel):
    """Origin information for a data asset."""

    uri: str = ""
    description: str = ""
    collection_method: str = ""
    geographic_origin: str = ""
    temporal_range: str = ""
    owner: str = ""


class QualityMetrics(BaseModel):
    """Data quality measurements."""

    completeness_score: float = 0.0
    consistency_score: float = 0.0
    freshness_score: float = 0.0
    accuracy_assessment: str = ""
    representativeness: str = ""
    error_rate: float | None = None
    row_count: int | None = None
    column_count: int | None = None


class BiasAssessment(BaseModel):
    """Bias detection and mitigation documentation."""

    methodology: str = ""
    protected_attributes_checked: list[str] = Field(default_factory=list)
    fairness_metrics: dict[str, float] = Field(default_factory=dict)
    mitigation_steps: list[str] = Field(default_factory=list)
    findings: str = ""


class ProcessDocumentation(BaseModel):
    """Data governance and preparation process."""

    governance_owner: str = ""
    preparation_methodology: str = ""
    review_process: str = ""
    last_review_date: str = ""
    labeling_procedure: str = ""
    anonymization_method: str = ""


class Article10Metadata(BaseModel):
    """EU AI Act Article 10 required metadata fields.

    Each field maps to a specific Article 10 requirement:
    - Art. 10(2)(a): data sources, lineage, chain of custody
    - Art. 10(2)(b): quality metrics, completeness, accuracy
    - Art. 10(2)(c): contextual appropriateness, intended use
    - Art. 10(2)(f): bias assessment, fairness metrics
    - Art. 10(4): data governance practices
    """

    # 1. Data source & lineage (Art. 10(2)(a))
    data_sources: list[DataSourceInfo] = Field(default_factory=list)
    chain_of_custody: list[dict[str, Any]] = Field(default_factory=list)
    provenance_records_count: int = 0
    merkle_chain_verified: bool = False

    # 2. Quality metrics (Art. 10(2)(b))
    quality: QualityMetrics = Field(default_factory=QualityMetrics)

    # 3. Contextual appropriateness (Art. 10(2)(c))
    intended_use: str = ""
    geographic_applicability: str = ""
    temporal_validity: str = ""
    population_coverage: str = ""
    known_limitations: list[str] = Field(default_factory=list)

    # 4. Bias assessment (Art. 10(2)(f))
    bias: BiasAssessment = Field(default_factory=BiasAssessment)

    # 5. Process documentation (Art. 10(4))
    process: ProcessDocumentation = Field(default_factory=ProcessDocumentation)

    # Computed
    trust_score: int | None = None
    trust_grade: str = ""
    compliance_gaps: list[str] = Field(default_factory=list)
    assessment_date: str = ""


class ComplianceGap(BaseModel):
    """A single compliance gap identified during assessment."""

    severity: str  # CRITICAL, WARNING, INFO
    article_ref: str  # e.g., "Art. 10(2)(a)"
    description: str
    recommendation: str = ""
