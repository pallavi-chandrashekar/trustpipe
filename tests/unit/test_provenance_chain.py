"""Tests for ProvenanceChain and ProvenanceRecord."""

from trustpipe.provenance.record import ProvenanceRecord, fingerprint_data


def test_track_creates_record(tp):
    record = tp.track({"rows": 100}, name="test_data", source="file://test.csv")
    assert record.id
    assert record.name == "test_data"
    assert record.source == "file://test.csv"
    assert record.merkle_root != ""
    assert record.merkle_index == 0


def test_track_requires_name(tp):
    import pytest
    from trustpipe.core.exceptions import ProvenanceError

    with pytest.raises(ProvenanceError):
        tp.track({"rows": 100}, name="")


def test_chain_integrity_after_multiple_appends(tp):
    r1 = tp.track({"rows": 100}, name="raw", source="s3://bucket/raw.csv")
    r2 = tp.track({"rows": 80}, name="clean", parent=r1.id)
    r3 = tp.track({"rows": 80}, name="features", parent=r2.id)

    assert tp.chain.verify(r1.id)
    assert tp.chain.verify(r2.id)
    assert tp.chain.verify(r3.id)
    assert r3.previous_root == r2.merkle_root


def test_trace_returns_chain_for_name(tp):
    tp.track({"rows": 100}, name="customers", source="db://prod/customers")
    tp.track({"rows": 100}, name="customers", source="db://prod/customers")

    chain = tp.trace("customers")
    assert len(chain) == 2
    assert chain[0].created_at <= chain[1].created_at


def test_trace_empty_for_unknown_name(tp):
    chain = tp.trace("nonexistent")
    assert chain == []


def test_parent_linkage(tp):
    r1 = tp.track({"rows": 100}, name="raw")
    r2 = tp.track({"rows": 80}, name="clean", parent=r1.id)

    assert r2.parent_ids == [r1.id]


def test_multiple_parents(tp):
    r1 = tp.track({"rows": 100}, name="table_a")
    r2 = tp.track({"rows": 200}, name="table_b")
    r3 = tp.track({"rows": 300}, name="joined", parents=[r1.id, r2.id])

    assert set(r3.parent_ids) == {r1.id, r2.id}


def test_verify_all_records(tp):
    tp.track({"rows": 100}, name="a")
    tp.track({"rows": 200}, name="b")
    tp.track({"rows": 300}, name="c")

    result = tp.verify()
    assert result["integrity"] == "OK"
    assert result["total"] == 3
    assert result["verified"] == 3
    assert result["failed"] == 0


def test_content_hash_deterministic():
    r = ProvenanceRecord(
        id="abc123",
        name="test",
        fingerprint="fp",
        column_names=["b", "a"],
    )
    h1 = r.content_hash()
    h2 = r.content_hash()
    assert h1 == h2
    assert len(h1) == 64  # SHA-256


def test_record_serialization():
    r = ProvenanceRecord(name="test", source="s3://bucket/data.csv", tags=["pii"])
    d = r.to_dict()
    r2 = ProvenanceRecord.from_dict(d)
    assert r2.name == "test"
    assert r2.source == "s3://bucket/data.csv"
    assert r2.tags == ["pii"]


def test_fingerprint_dict_data():
    fp = fingerprint_data({"rows": 100, "columns": 5})
    assert fp["fingerprint"]
    assert fp["row_count"] == 100


def test_status(tp):
    tp.track({"rows": 100}, name="test")
    info = tp.status()
    assert info["project"] == "default"
    assert info["record_count"] == 1
    assert info["chain_length"] == 1
    assert info["chain_root"] is not None
