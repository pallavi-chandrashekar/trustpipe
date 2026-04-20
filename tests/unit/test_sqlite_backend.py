"""Tests for SQLite storage backend."""

from trustpipe.provenance.record import ProvenanceRecord


def test_initialize_creates_tables(storage):
    # If we get here without error, tables were created
    count = storage.get_record_count()
    assert count == 0


def test_save_and_load_record(storage):
    record = ProvenanceRecord(
        id="test123",
        name="test_data",
        source="s3://bucket/data.csv",
        fingerprint="abc123",
        row_count=100,
        column_names=["a", "b", "c"],
        merkle_root="root_hash",
        merkle_index=0,
        tags=["training"],
        metadata={"key": "value"},
    )
    storage.save_provenance_record(record)

    loaded = storage.load_provenance_record("test123")
    assert loaded is not None
    assert loaded.name == "test_data"
    assert loaded.source == "s3://bucket/data.csv"
    assert loaded.row_count == 100
    assert loaded.column_names == ["a", "b", "c"]
    assert loaded.tags == ["training"]
    assert loaded.metadata == {"key": "value"}


def test_load_nonexistent_returns_none(storage):
    assert storage.load_provenance_record("nonexistent") is None


def test_query_by_name(storage):
    for i in range(3):
        record = ProvenanceRecord(
            id=f"rec_{i}",
            name="customers",
            fingerprint=f"fp_{i}",
            merkle_root=f"root_{i}",
            merkle_index=i,
        )
        storage.save_provenance_record(record)

    results = storage.query_provenance_by_name("customers")
    assert len(results) == 3


def test_query_by_name_empty(storage):
    results = storage.query_provenance_by_name("nonexistent")
    assert results == []


def test_merkle_hash_storage(storage):
    storage.save_merkle_hash(0, "hash_0")
    storage.save_merkle_hash(1, "hash_1")
    storage.save_merkle_hash(2, "hash_2")

    hashes = storage.load_merkle_hashes()
    assert hashes == ["hash_0", "hash_1", "hash_2"]


def test_record_count(storage):
    assert storage.get_record_count() == 0

    for i in range(5):
        record = ProvenanceRecord(
            id=f"rec_{i}",
            name=f"data_{i}",
            fingerprint=f"fp_{i}",
            merkle_root=f"root_{i}",
            merkle_index=i,
        )
        storage.save_provenance_record(record)

    assert storage.get_record_count() == 5


def test_latest_records(storage):
    for i in range(10):
        record = ProvenanceRecord(
            id=f"rec_{i}",
            name=f"data_{i}",
            fingerprint=f"fp_{i}",
            merkle_root=f"root_{i}",
            merkle_index=i,
        )
        storage.save_provenance_record(record)

    latest = storage.get_latest_records(limit=3)
    assert len(latest) == 3


def test_trust_score_save_and_load(storage):
    import uuid
    from datetime import datetime, timezone

    score_data = {
        "id": uuid.uuid4().hex[:12],
        "record_id": "rec_0",
        "dataset_name": "test",
        "composite": 85,
        "grade": "A",
        "dimensions": [{"name": "Freshness", "raw_score": 0.9}],
        "warnings": [],
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "config_snapshot": {},
        "project": "default",
    }
    storage.save_trust_score(score_data)

    loaded = storage.load_latest_trust_score("test")
    assert loaded is not None
    assert loaded["composite"] == 85
    assert loaded["grade"] == "A"
