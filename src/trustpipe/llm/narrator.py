"""LLM-enhanced compliance narrative generation (optional)."""

from __future__ import annotations

from typing import Optional

from trustpipe.compliance.schemas import Article10Metadata, ComplianceGap
from trustpipe.llm.providers import LLMProvider


def generate_compliance_narrative(
    metadata: Article10Metadata,
    gaps: list[ComplianceGap],
    provider: LLMProvider,
    dataset_name: str = "",
) -> str:
    """Generate a human-readable compliance narrative using an LLM.

    This enhances the structured report with prose explanations
    suitable for submission to regulators or auditors.
    """
    prompt = f"""You are writing an EU AI Act Article 10 compliance narrative for a dataset called "{dataset_name}".

Based on the following structured data, write a clear, professional 3-5 paragraph narrative suitable for regulatory submission. Focus on what is well-documented, acknowledge gaps honestly, and suggest next steps.

**Data Summary:**
- Sources: {len(metadata.data_sources)} documented
- Provenance records: {metadata.provenance_records_count}
- Merkle chain verified: {metadata.merkle_chain_verified}
- Trust score: {metadata.trust_score}/100 ({metadata.trust_grade})
- Completeness: {metadata.quality.completeness_score:.0%}
- Consistency: {metadata.quality.consistency_score:.0%}
- Intended use: {metadata.intended_use or 'Not documented'}
- Bias methodology: {metadata.bias.methodology or 'Not documented'}
- Governance owner: {metadata.process.governance_owner or 'Not assigned'}

**Compliance Gaps ({len(gaps)} total):**
{chr(10).join(f'- [{g.severity}] {g.article_ref}: {g.description}' for g in gaps)}

Write the narrative in professional English. Do not invent data — only reference what is provided above."""

    return provider.generate(prompt, max_tokens=1500)


def generate_gap_remediation_plan(
    gaps: list[ComplianceGap],
    provider: LLMProvider,
) -> str:
    """Generate a prioritized remediation plan for compliance gaps."""
    if not gaps:
        return "No compliance gaps identified. All Article 10 requirements are met."

    prompt = f"""You are a data governance advisor. Create a prioritized remediation plan for these EU AI Act Article 10 compliance gaps:

{chr(10).join(f'- [{g.severity}] {g.article_ref}: {g.description} → Recommendation: {g.recommendation}' for g in gaps)}

Format as a numbered action plan ordered by priority (CRITICAL first). For each item include:
1. Action to take
2. Estimated effort (hours/days)
3. Who should own it (role, not person)

Be concise and actionable."""

    return provider.generate(prompt, max_tokens=1000)
