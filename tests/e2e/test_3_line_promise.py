"""The 3-line promise test — literally tests the claim from the README."""

import pandas as pd


def test_three_line_promise(tmp_path):
    """The promise: 3 lines added to existing code gives you provenance + trust."""
    # === User's existing code ===
    df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})

    # === The 3 lines ===
    from trustpipe import TrustPipe               # Line 1
    tp = TrustPipe(db_path=tmp_path / "test.db")  # Line 2
    tp.track(df, name="my_data")                   # Line 3

    # === Verify provenance works ===
    chain = tp.trace("my_data")
    assert len(chain) == 1
    assert chain[0].row_count == 3
    assert chain[0].column_names == ["x", "y"]

    # === Verify trust scoring works ===
    score = tp.score(df, name="my_data")
    assert 0 <= score.composite <= 100
    assert score.grade in ("A+", "A", "B", "C", "D", "F")
    assert len(score.dimensions) == 6

    # === Verify integrity works ===
    result = tp.verify()
    assert result["integrity"] == "OK"


def test_pipeline_with_parent_linkage(tmp_path):
    """Test a realistic multi-step pipeline with parent tracking."""
    from trustpipe import TrustPipe

    tp = TrustPipe(db_path=tmp_path / "test.db")

    # Raw data
    raw = pd.DataFrame({"user_id": range(1000), "amount": [i * 1.5 for i in range(1000)]})
    r1 = tp.track(raw, name="raw_transactions", source="s3://data/raw/")

    # Clean data (remove outliers)
    clean = raw[raw["amount"] < 1000]
    r2 = tp.track(clean, name="clean_transactions", parent=r1.id)

    # Feature engineering
    features = clean.copy()
    features["amount_log"] = features["amount"].apply(lambda x: x + 1)
    r3 = tp.track(features, name="features", parent=r2.id)

    # Verify chain
    assert tp.chain.verify(r1.id)
    assert tp.chain.verify(r2.id)
    assert tp.chain.verify(r3.id)

    # Score the final output
    score = tp.score(features, name="features")
    assert score.composite > 0

    # Lineage should show parent chain
    ancestors = tp.chain.get_ancestors(r3.id)
    assert len(ancestors) == 3
