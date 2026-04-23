# EU AI Act Compliance Guide

TrustPipe generates compliance documentation for **EU AI Act Article 10** — the data governance requirements for high-risk AI systems. Enforcement begins **August 2, 2026**.

## What Article 10 Requires

| Requirement | Article | What TrustPipe Provides |
|-------------|---------|------------------------|
| Data source documentation | 10(2)(a) | Automatic from `tp.track(source=...)` |
| Chain of custody | 10(2)(a) | Merkle-backed provenance chain |
| Quality metrics | 10(2)(b) | Trust score (completeness, consistency, freshness) |
| Accuracy assessment | 10(2)(b) | *User-supplied* — TrustPipe flags if missing |
| Contextual appropriateness | 10(2)(c) | *User-supplied* via `user_metadata` |
| Bias assessment | 10(2)(f) | *User-supplied* — TrustPipe flags if missing |
| Data governance process | 10(4) | *User-supplied* — TrustPipe flags if missing |

**TrustPipe auto-fills** what can be derived from provenance + trust data, and **identifies gaps** where human input is needed.

## Generating a Report

### Python

```python
report = tp.comply(
    "training_set",
    regulation="eu-ai-act-article-10",
    user_metadata={
        "intended_use": "Credit scoring model for loan applications",
        "geographic_applicability": "European Union",
        "population_coverage": "Adults 18+ with credit history",
        "known_limitations": ["US-centric training data"],
    },
)
print(report)  # Markdown report
```

### CLI

```bash
trustpipe comply training_set --output article10_report.md
trustpipe comply training_set --regulation datacard --output datacard.md
trustpipe comply training_set --format json  # machine-readable
```

## Report Types

| Type | Command | Purpose |
|------|---------|---------|
| **EU AI Act Article 10** | `--regulation eu-ai-act-article-10` | Full regulatory compliance report |
| **Data Card** | `--regulation datacard` | Concise dataset summary |
| **Audit Log** | `--regulation audit-log` | Chain of custody with Merkle hashes |

## Gap Analysis

TrustPipe checks 10 compliance points:

| # | Check | Severity | Article |
|---|-------|----------|---------|
| 1 | Data sources documented | CRITICAL | 10(2)(a) |
| 2 | Chain of custody recorded | CRITICAL | 10(2)(a) |
| 3 | Merkle chain verified | WARNING | 10(2)(a) |
| 4 | Completeness above 70% | WARNING | 10(2)(b) |
| 5 | Accuracy assessment documented | WARNING | 10(2)(b) |
| 6 | Intended use documented | WARNING | 10(2)(c) |
| 7 | Geographic applicability specified | INFO | 10(2)(c) |
| 8 | Bias methodology documented | CRITICAL | 10(2)(f) |
| 9 | Protected attributes checked | WARNING | 10(2)(f) |
| 10 | Governance owner assigned | WARNING | 10(4) |

### Reading the Gap Analysis

```
[!!] Art. 10(2)(f): No bias assessment methodology documented
     -> Document methods used to detect and mitigate bias

[!]  Art. 10(2)(c): Intended use not documented
     -> Specify the AI system's intended purpose

[i]  Art. 10(4): Data preparation methodology not documented
     -> Document sampling, filtering, anonymization procedures
```

- `CRITICAL` — Must fix before compliance submission
- `WARNING` — Should fix, regulators may ask
- `INFO` — Best practice, strengthens your case

## Filling in User-Supplied Fields

Pass `user_metadata` to provide information TrustPipe can't auto-detect:

```python
tp.comply("dataset", user_metadata={
    # Article 10(2)(c)
    "intended_use": "Fraud detection for payment processing",
    "geographic_applicability": "US, EU, UK",
    "temporal_validity": "2024-2026 transaction data",
    "population_coverage": "Online retail customers",
    "known_limitations": ["Excludes in-store transactions"],

    # Article 10(2)(f) — bias
    # (Provide via separate bias assessment tooling)

    # Article 10(4) — governance
    # (Provide via your organization's governance process)
})
```

## Optional: LLM-Enhanced Narratives

With an LLM provider configured, TrustPipe can generate prose narratives suitable for regulatory submission:

```yaml
# trustpipe.yaml
llm:
  llm_provider: anthropic
  llm_model: claude-sonnet-4-20250514
```

This is entirely optional. Core compliance reports work without any LLM.
