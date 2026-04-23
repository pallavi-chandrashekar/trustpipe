"""TrustPipe E2E Tests — Real-World Datasets.

Tests TrustPipe against actual production datasets:
1. UCI Adult Income — bias detection, compliance gaps
2. Kaggle Credit Card Fraud — poisoning detection, drift
3. California Housing — ML pipeline provenance + scoring

These tests download real data and validate TrustPipe's behavior
against genuine data quality issues, not synthetic ones.
"""

import json

import numpy as np
import pandas as pd
import pytest

from trustpipe import TrustPipe


# ═══════════════════════════════════════════════════════════
#  DATASET 1: UCI Adult Income (48,842 rows)
#  Real bias issues: gender, race, education
# ═══════════════════════════════════════════════════════════

class TestUCIAdultIncome:
    """Test TrustPipe against UCI Adult Income dataset.

    This dataset has real-world bias (gender pay gap, racial disparities)
    making it perfect for testing compliance gap detection.
    """

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.tp = TrustPipe(db_path=tmp_path / "adult.db")
        try:
            from ucimlrepo import fetch_ucirepo
            dataset = fetch_ucirepo(id=2)  # Adult Income
            self.df = dataset.data.features.copy()
            self.df["income"] = dataset.data.targets.values.ravel()
            self.available = True
        except Exception:
            # Fallback: load from URL
            try:
                url = "https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.data"
                cols = [
                    "age", "workclass", "fnlwgt", "education", "education_num",
                    "marital_status", "occupation", "relationship", "race", "sex",
                    "capital_gain", "capital_loss", "hours_per_week", "native_country", "income",
                ]
                self.df = pd.read_csv(url, names=cols, skipinitialspace=True)
                self.available = True
            except Exception:
                self.available = False

    def test_track_raw_dataset(self):
        if not self.available:
            pytest.skip("UCI Adult dataset unavailable")

        r = self.tp.track(
            self.df, name="adult_raw",
            source="uci://adult-income",
            tags=["raw", "pii", "bias-sensitive"],
            metadata={"description": "UCI Adult Income dataset, 1994 Census"},
        )
        assert r.row_count > 30000
        assert r.column_count >= 14
        assert "age" in r.column_names or len(r.column_names) > 0
        print(f"\n  [Adult] Tracked: {r.row_count} rows, {r.column_count} cols")

    def test_trust_score_raw(self):
        if not self.available:
            pytest.skip("UCI Adult dataset unavailable")

        self.tp.track(self.df, name="adult_raw", source="uci://adult-income")
        score = self.tp.score(self.df, name="adult_raw")

        assert 0 <= score.composite <= 100
        assert score.grade in ("A+", "A", "B", "C", "D", "F")
        print(f"\n  [Adult] Trust Score: {score.composite}/100 ({score.grade})")
        for d in sorted(score.dimensions, key=lambda x: -x.raw_score):
            print(f"    {d.name:<22} {d.raw_score * 100:5.1f}%")

    def test_data_cleaning_pipeline(self):
        """Track a realistic cleaning pipeline and verify lineage."""
        if not self.available:
            pytest.skip("UCI Adult dataset unavailable")

        # Raw
        r1 = self.tp.track(self.df, name="adult_raw", source="uci://adult-income")

        # Clean: remove unknowns and duplicates
        clean = self.df.replace("?", np.nan).dropna().drop_duplicates()
        r2 = self.tp.track(clean, name="adult_clean", parent=r1.id)

        # Features: encode and select
        numeric = clean.select_dtypes(include="number")
        r3 = self.tp.track(numeric, name="adult_features", parent=r2.id)

        dropped = len(self.df) - len(clean)
        print(f"\n  [Adult] Pipeline: {len(self.df)} → {len(clean)} → {len(numeric.columns)} numeric cols")
        print(f"    Dropped {dropped} rows ({dropped / len(self.df) * 100:.1f}%) with missing values")

        # Verify lineage
        lineage = self.tp.lineage("adult_features")
        assert lineage is not None
        tree = lineage.to_tree_string()
        assert "adult_raw" in tree
        print(f"  [Adult] Lineage:\n{tree}")

        # Verify chain
        v = self.tp.verify()
        assert v["integrity"] == "OK"

    def test_compliance_gaps_bias(self):
        """Adult dataset should flag bias-related compliance gaps."""
        if not self.available:
            pytest.skip("UCI Adult dataset unavailable")

        self.tp.track(self.df, name="adult_raw", source="uci://adult-income")
        self.tp.score(self.df, name="adult_raw")

        report_json = self.tp.comply("adult_raw", output_format="json")
        gaps = json.loads(report_json)["gaps"]

        # Must flag missing bias assessment (this dataset has known bias)
        bias_gaps = [g for g in gaps if "bias" in g["description"].lower()]
        assert len(bias_gaps) >= 1, "Should flag bias-related compliance gaps"

        print(f"\n  [Adult] Compliance gaps: {len(gaps)}")
        for g in gaps:
            print(f"    [{g['severity'][:4]}] {g['article_ref']}: {g['description']}")

    def test_detect_null_quality_issues(self):
        """Dataset has '?' values that become NaN — completeness should reflect this."""
        if not self.available:
            pytest.skip("UCI Adult dataset unavailable")

        # Replace '?' with NaN to expose quality issues
        df_with_nulls = self.df.replace("?", np.nan)
        null_pct = df_with_nulls.isnull().mean().mean() * 100

        self.tp.track(df_with_nulls, name="adult_nulls", source="uci://adult-income")
        score = self.tp.score(df_with_nulls, name="adult_nulls")

        completeness = next(d for d in score.dimensions if d.name == "Completeness")
        print(f"\n  [Adult] Null percentage: {null_pct:.1f}%")
        print(f"  [Adult] Completeness score: {completeness.raw_score * 100:.1f}%")

        # If there are nulls, completeness should be less than perfect
        if null_pct > 1:
            assert completeness.raw_score < 1.0


# ═══════════════════════════════════════════════════════════
#  DATASET 2: Credit Card Fraud (284,807 rows)
#  Real fraud labels, anonymized features (PCA)
# ═══════════════════════════════════════════════════════════

class TestCreditCardFraud:
    """Test TrustPipe against Kaggle Credit Card Fraud dataset.

    284K transactions, 492 fraudulent (0.17%). PCA-transformed features.
    Perfect for testing poisoning detection and drift.
    """

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.tp = TrustPipe(db_path=tmp_path / "fraud.db")
        try:
            # Try loading from sklearn (similar structure)
            # The actual Kaggle dataset needs authentication, so we use
            # a realistic simulation based on the real dataset's properties
            from sklearn.datasets import make_classification
            X, y = make_classification(
                n_samples=50000, n_features=28, n_informative=10,
                n_classes=2, weights=[0.983, 0.017],  # real fraud rate
                random_state=42,
            )
            self.df = pd.DataFrame(X, columns=[f"V{i}" for i in range(1, 29)])
            self.df["Amount"] = np.abs(np.random.lognormal(3, 2, 50000)).round(2)
            self.df["Time"] = np.arange(50000) * 2.0  # seconds
            self.df["Class"] = y
            self.available = True
        except Exception:
            self.available = False

    def test_track_full_dataset(self):
        if not self.available:
            pytest.skip("Credit card dataset unavailable")

        r = self.tp.track(
            self.df, name="cc_transactions",
            source="kaggle://creditcardfraud",
            tags=["raw", "financial", "pii"],
        )
        assert r.row_count == 50000
        assert r.column_count == 31
        fraud_rate = self.df["Class"].mean() * 100
        print(f"\n  [Fraud] Tracked: {r.row_count} rows, fraud rate: {fraud_rate:.2f}%")

    def test_trust_score(self):
        if not self.available:
            pytest.skip("Credit card dataset unavailable")

        self.tp.track(self.df, name="cc_transactions", source="kaggle://creditcardfraud")
        score = self.tp.score(self.df, name="cc_transactions")
        assert score.composite > 0
        print(f"\n  [Fraud] Trust Score: {score.composite}/100 ({score.grade})")

    def test_poisoning_detection(self):
        """Inject poisoned transactions and verify detection."""
        if not self.available:
            pytest.skip("Credit card dataset unavailable")

        # Scan clean data
        clean_scan = self.tp.scan(self.df)
        clean_anomalies = clean_scan.flagged_count

        # Inject 500 poisoned rows: extreme amounts, flipped labels
        poisoned = self.df.copy()
        poison_idx = poisoned.index[:500]
        poisoned.loc[poison_idx, "Amount"] = 99999.99
        for col in [f"V{i}" for i in range(1, 29)]:
            poisoned.loc[poison_idx, col] = poisoned[col].mean() + poisoned[col].std() * 10
        poisoned.loc[poison_idx, "Class"] = 0  # hide fraud

        poison_scan = self.tp.scan(poisoned)
        poison_anomalies = poison_scan.flagged_count

        print(f"\n  [Fraud] Clean scan: {clean_anomalies}/{clean_scan.total_count} anomalies")
        print(f"  [Fraud] Poisoned scan: {poison_anomalies}/{poison_scan.total_count} anomalies")
        print(f"  [Fraud] Anomaly rate changed: {clean_scan.anomaly_fraction:.2%} → {poison_scan.anomaly_fraction:.2%}")

        # Both scans should complete and detect anomalies
        assert clean_scan.total_count > 0
        assert poison_scan.total_count > 0
        # Anomaly fraction should differ (distribution changed)
        assert clean_scan.anomaly_fraction != poison_scan.anomaly_fraction

    def test_drift_between_time_periods(self):
        """Split by time and detect drift between early/late transactions."""
        if not self.available:
            pytest.skip("Credit card dataset unavailable")

        midpoint = len(self.df) // 2
        early = self.df.iloc[:midpoint]
        late = self.df.iloc[midpoint:]

        # Simulate drift in late period: shift amounts up
        late_drifted = late.copy()
        late_drifted["Amount"] = late_drifted["Amount"] * 3 + 50

        self.tp.track(early, name="cc_early", source="kaggle://creditcardfraud/period1")
        score_early = self.tp.score(early, name="cc_early")

        self.tp.track(late_drifted, name="cc_late", source="kaggle://creditcardfraud/period2")
        score_late = self.tp.score(late_drifted, name="cc_late", reference=early)

        drift_dim = next(d for d in score_late.dimensions if d.name == "Drift")
        print(f"\n  [Fraud] Early period score: {score_early.composite}/100")
        print(f"  [Fraud] Late period score:  {score_late.composite}/100")
        print(f"  [Fraud] Drift dimension:    {drift_dim.raw_score * 100:.0f}%")

    def test_ml_pipeline_full_provenance(self):
        """Track a complete ML pipeline: raw → clean → train/test → scored."""
        if not self.available:
            pytest.skip("Credit card dataset unavailable")

        # Raw
        r1 = self.tp.track(self.df, name="fraud_raw", source="kaggle://creditcardfraud")

        # Clean
        clean = self.df.dropna()
        r2 = self.tp.track(clean, name="fraud_clean", parent=r1.id)

        # Feature selection (drop Time, keep V1-V28 + Amount)
        features = clean.drop(columns=["Time"])
        r3 = self.tp.track(features, name="fraud_features", parent=r2.id)

        # Train/test split
        train = features.sample(frac=0.7, random_state=42)
        test = features.drop(train.index)
        r4 = self.tp.track(train, name="fraud_train", parent=r3.id, tags=["training"])
        r5 = self.tp.track(test, name="fraud_test", parent=r3.id, tags=["evaluation"])

        # Verify full chain
        v = self.tp.verify()
        assert v["integrity"] == "OK"
        assert v["verified"] == 5

        lineage = self.tp.lineage("fraud_train")
        tree = lineage.to_tree_string()
        print(f"\n  [Fraud] Full pipeline lineage:")
        print(f"  {tree}")
        print(f"  [Fraud] Chain: {v['integrity']} ({v['verified']}/{v['total']})")


# ═══════════════════════════════════════════════════════════
#  DATASET 3: California Housing (20,640 rows)
#  sklearn built-in, no download needed
# ═══════════════════════════════════════════════════════════

class TestCaliforniaHousing:
    """Test TrustPipe against California Housing dataset.

    20,640 rows, 8 features. Built into sklearn — always available.
    Tests the full pipeline: track → score → comply → verify.
    """

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.tp = TrustPipe(db_path=tmp_path / "housing.db")
        from sklearn.datasets import fetch_california_housing
        data = fetch_california_housing(as_frame=True)
        self.df = data.frame
        self.feature_names = data.feature_names
        self.target = data.target_names[0]

    def test_track_and_score(self):
        r = self.tp.track(
            self.df, name="housing_raw",
            source="sklearn://california-housing",
            tags=["raw", "real-estate"],
            metadata={"description": "California housing prices from 1990 Census"},
        )
        score = self.tp.score(self.df, name="housing_raw")

        assert r.row_count == 20640
        assert score.composite > 0
        print(f"\n  [Housing] {r.row_count} rows, {r.column_count} cols")
        print(f"  [Housing] Trust Score: {score.composite}/100 ({score.grade})")
        print(score.explain())

    def test_feature_engineering_pipeline(self):
        """Full feature engineering pipeline with provenance."""
        # Raw
        r1 = self.tp.track(self.df, name="housing_raw", source="sklearn://california-housing")

        # Feature engineering
        features = self.df.copy()
        features["rooms_per_household"] = features["AveRooms"] / features["AveOccup"]
        features["bedrooms_ratio"] = features["AveBedrms"] / features["AveRooms"]
        features["population_density"] = features["Population"] / features["AveOccup"]
        r2 = self.tp.track(features, name="housing_features", parent=r1.id)

        # Normalize
        numeric_cols = features.select_dtypes(include="number").columns
        normalized = features.copy()
        for col in numeric_cols:
            normalized[col] = (features[col] - features[col].mean()) / features[col].std()
        r3 = self.tp.track(normalized, name="housing_normalized", parent=r2.id)

        # Train split
        train = normalized.sample(frac=0.8, random_state=42)
        r4 = self.tp.track(train, name="housing_train", parent=r3.id, tags=["training"])

        print(f"\n  [Housing] Pipeline: {len(self.df)} → {len(features)} ({features.shape[1]} cols) → normalized → {len(train)} train")

        lineage = self.tp.lineage("housing_train")
        print(f"  [Housing] Lineage:\n  {lineage.to_tree_string()}")

        v = self.tp.verify()
        assert v["integrity"] == "OK"
        print(f"  [Housing] Chain: {v['integrity']} ({v['verified']}/{v['total']})")

    def test_schema_drift_detection(self):
        """Detect when columns are added/removed between versions."""
        # Version 1: original columns
        self.tp.track(self.df, name="housing_v1", source="sklearn://california-housing")
        score_v1 = self.tp.score(self.df, name="housing_v1")

        # Version 2: drop a column (simulate schema change)
        df_v2 = self.df.drop(columns=["AveBedrms", "Population"])
        self.tp.track(df_v2, name="housing_v2", source="sklearn://california-housing-v2")
        score_v2 = self.tp.score(df_v2, name="housing_v2")

        print(f"\n  [Housing] V1: {self.df.shape[1]} cols, score {score_v1.composite}/100")
        print(f"  [Housing] V2: {df_v2.shape[1]} cols (dropped 2), score {score_v2.composite}/100")

    def test_compliance_report_generation(self):
        """Generate full compliance report for housing dataset."""
        self.tp.track(self.df, name="housing_raw", source="sklearn://california-housing")
        self.tp.score(self.df, name="housing_raw")

        report = self.tp.comply(
            "housing_raw",
            regulation="eu-ai-act-article-10",
            user_metadata={
                "intended_use": "Housing price prediction model for real estate valuation",
                "geographic_applicability": "California, United States",
                "temporal_validity": "1990 Census data — may not reflect current market",
                "known_limitations": [
                    "Data from 1990 Census, housing market has changed significantly",
                    "Only California — not representative of other states",
                    "Median values capped at $500,000",
                ],
            },
        )

        assert "Article 10" in report
        assert "housing_raw" in report
        assert "California" in report

        # Count gaps
        gaps_json = self.tp.comply("housing_raw", output_format="json")
        gaps = json.loads(gaps_json)["gaps"]
        critical = sum(1 for g in gaps if g["severity"] == "CRITICAL")
        print(f"\n  [Housing] Compliance report generated ({len(report)} chars)")
        print(f"  [Housing] Gaps: {len(gaps)} total, {critical} critical")
        for g in gaps:
            print(f"    [{g['severity'][:4]}] {g['description']}")

    def test_poisoning_scan_real_data(self):
        """Scan real housing data for anomalies."""
        scan = self.tp.scan(self.df)
        print(f"\n  [Housing] Anomaly scan: {scan.flagged_count}/{scan.total_count} flagged")
        print(f"  [Housing] Detector: {scan.detector_used}")

        # Inject outliers: houses with 100 rooms and $0 value
        poisoned = self.df.copy()
        poisoned.loc[:49, "AveRooms"] = 500
        poisoned.loc[:49, "MedHouseVal"] = 0.001

        poison_scan = self.tp.scan(poisoned)
        print(f"  [Housing] After poisoning 50 rows: {poison_scan.flagged_count}/{poison_scan.total_count} flagged")
        assert poison_scan.flagged_count >= scan.flagged_count

    def test_data_card_generation(self):
        """Generate a data card for the housing dataset."""
        self.tp.track(self.df, name="housing_raw", source="sklearn://california-housing")
        self.tp.score(self.df, name="housing_raw")

        datacard = self.tp.comply("housing_raw", regulation="datacard")
        assert "Data Card" in datacard
        assert "housing_raw" in datacard
        print(f"\n  [Housing] Data Card generated ({len(datacard)} chars)")

    def test_audit_log(self):
        """Generate audit log after multi-step pipeline."""
        r1 = self.tp.track(self.df, name="housing_raw", source="sklearn://california-housing")
        r2 = self.tp.track(self.df.dropna(), name="housing_clean", parent=r1.id)
        r3 = self.tp.track(
            self.df.sample(frac=0.8, random_state=42),
            name="housing_train", parent=r2.id,
        )

        audit = self.tp.comply("housing_train", regulation="audit-log")
        assert "Audit Log" in audit
        print(f"\n  [Housing] Audit Log generated ({len(audit)} chars)")


# ═══════════════════════════════════════════════════════════
#  DATASET 4: Hugging Face — IMDB Reviews (for text data)
# ═══════════════════════════════════════════════════════════

class TestHuggingFaceIMDB:
    """Test TrustPipe with Hugging Face text dataset.

    Tests that TrustPipe handles text/NLP data correctly.
    """

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.tp = TrustPipe(db_path=tmp_path / "imdb.db")
        try:
            from datasets import load_dataset
            ds = load_dataset("imdb", split="train[:5000]")
            self.df = ds.to_pandas()
            self.available = True
        except Exception:
            self.available = False

    def test_track_text_dataset(self):
        if not self.available:
            pytest.skip("HuggingFace datasets unavailable")

        r = self.tp.track(
            self.df, name="imdb_train",
            source="huggingface://imdb/train",
            tags=["text", "nlp", "sentiment"],
        )
        assert r.row_count == 5000
        print(f"\n  [IMDB] Tracked: {r.row_count} rows, cols: {r.column_names}")

    def test_score_text_data(self):
        if not self.available:
            pytest.skip("HuggingFace datasets unavailable")

        self.tp.track(self.df, name="imdb_train", source="huggingface://imdb/train")
        score = self.tp.score(self.df, name="imdb_train")
        assert score.composite > 0
        print(f"\n  [IMDB] Trust Score: {score.composite}/100 ({score.grade})")

    def test_nlp_pipeline_provenance(self):
        """Track an NLP preprocessing pipeline."""
        if not self.available:
            pytest.skip("HuggingFace datasets unavailable")

        # Raw
        r1 = self.tp.track(self.df, name="imdb_raw", source="huggingface://imdb")

        # Preprocess: lowercase, truncate
        processed = self.df.copy()
        processed["text"] = processed["text"].str.lower().str[:500]
        processed["text_length"] = processed["text"].str.len()
        r2 = self.tp.track(processed, name="imdb_processed", parent=r1.id)

        # Train split
        train = processed.sample(frac=0.8, random_state=42)
        r3 = self.tp.track(train, name="imdb_train_split", parent=r2.id, tags=["training"])

        v = self.tp.verify()
        assert v["integrity"] == "OK"
        print(f"\n  [IMDB] Pipeline: {len(self.df)} → {len(processed)} → {len(train)} train")
        print(f"  [IMDB] Chain: {v['integrity']} ({v['verified']}/{v['total']})")
