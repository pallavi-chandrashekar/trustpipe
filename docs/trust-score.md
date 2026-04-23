# Trust Score Guide

TrustPipe assigns a **Trust Score (0-100)** to every data asset, computed across six dimensions.

## The Score

```
Trust Score: 89/100 (Grade: A)

  Completeness           ████████████████████ 100.0 (w=0.20)
  Consistency            ████████████████████ 100.0 (w=0.20)
  Freshness              ███████████████████░ 100.0 (w=0.15)
  Provenance Depth       ██████████████████░░  90.0 (w=0.15)
  Drift                  ████████████████░░░░  80.0 (w=0.15)
  Poisoning Risk         ██████████████░░░░░░  70.0 (w=0.15)
```

## Grade Scale

| Grade | Range | Meaning |
|-------|-------|---------|
| A+ | 95-100 | Excellent — fully trusted |
| A | 85-94 | Good — minor gaps |
| B | 70-84 | Acceptable — some concerns |
| C | 55-69 | Below threshold — investigate |
| D | 40-54 | Poor — significant issues |
| F | 0-39 | Critical — do not use for AI training |

## Six Dimensions

### 1. Provenance Depth (weight: 0.15)

*How well-documented is the data's origin?*

| Score | Meaning |
|-------|---------|
| 1.0 | Full chain with source, parents, and Merkle verification |
| 0.7 | Source URI + parent linkage present |
| 0.5 | Source declared but no parent chain |
| 0.2 | Record exists but no source |
| 0.0 | No provenance recorded |

### 2. Freshness (weight: 0.15)

*How recent is the data?*

Exponential decay formula: `score = exp(-ln(2) * age_days / half_life)`

Default half-life: 30 days. A 30-day-old dataset scores 50%. A 90-day-old dataset scores 12.5%.

Configure: `freshness_half_life_days` in `trustpipe.yaml`.

### 3. Completeness (weight: 0.20)

*What fraction of expected data is present?*

- Base: `1 - mean_null_ratio` across all columns
- Penalty if row count is < 50% of historical (suggests data loss)
- A dataset with zero nulls scores 1.0

### 4. Consistency (weight: 0.20)

*Does the data conform to expected schema?*

Compares against previous version:
- Missing columns: penalty per column
- Extra columns: smaller penalty
- Dtype changes: 0.1 penalty per changed column
- First version (no history): scores 1.0

### 5. Drift (weight: 0.15)

*Has the data distribution shifted?*

Requires a reference dataset. Uses [evidently](https://www.evidentlyai.com/) for statistical tests:
- Numerical: Kolmogorov-Smirnov or Wasserstein distance
- Categorical: Jensen-Shannon divergence

Score = `1 - fraction_of_drifted_columns`

Falls back to simple mean/std comparison if evidently isn't installed.

### 6. Poisoning Risk (weight: 0.15)

*Likelihood the data has been tampered with.*

Uses [PyOD](https://pyod.readthedocs.io/) Isolation Forest for anomaly detection:
- Scores each row for anomaly likelihood
- Computes `anomaly_fraction` (fraction flagged as outliers)
- Low anomaly fraction = high trust

Falls back to z-score outlier detection (|z| > 3) if PyOD isn't installed.

## Customizing Weights

In `trustpipe.yaml`:

```yaml
scoring:
  weight_provenance_depth: 0.15
  weight_freshness: 0.15
  weight_completeness: 0.20
  weight_consistency: 0.20
  weight_drift: 0.15
  weight_poisoning_risk: 0.15
```

Weights must sum to 1.0.

## Scoring Specific Dimensions

```python
# Score only completeness and drift
score = tp.score(df, name="data", checks=["Completeness", "Drift"])
```

## Using Scores in CI/CD

```bash
# Fail build if score < 70
trustpipe gate my_dataset --threshold 70
```
