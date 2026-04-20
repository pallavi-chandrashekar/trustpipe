"""LLM-enhanced semantic analysis for data quality (optional)."""

from __future__ import annotations

from typing import Any

from trustpipe.llm.providers import LLMProvider


def analyze_data_semantics(
    data_summary: dict[str, Any],
    provider: LLMProvider,
    context: str = "",
) -> str:
    """Use an LLM to analyze data for semantic anomalies.

    Statistical detectors catch numerical outliers. This catches
    semantic issues: values that are technically valid but contextually
    wrong (e.g., a salary of $1 or an age of 200).
    """
    prompt = f"""Analyze this dataset summary for potential data quality issues, anomalies, or signs of data poisoning.

**Dataset Summary:**
- Row count: {data_summary.get("row_count", "Unknown")}
- Columns: {data_summary.get("column_names", [])}
- Null ratios: {data_summary.get("null_ratios", {})}
- Data types: {data_summary.get("dtypes", {})}

{f"**Context:** {context}" if context else ""}

Look for:
1. Semantic anomalies (values that are technically valid but suspicious)
2. Distribution concerns (unusual patterns in null ratios or types)
3. Schema concerns (unexpected column names or types)
4. Potential data poisoning indicators

Be concise. Flag only genuine concerns, not theoretical risks."""

    return provider.generate(prompt, max_tokens=800)
