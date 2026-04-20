"""Tests for S3 backend — uses mocked boto3 to avoid real AWS dependency."""

from unittest.mock import patch

import pytest


def test_s3_import_error():
    """S3Backend should raise helpful error if boto3 not installed."""
    with patch.dict("sys.modules", {"boto3": None}):
        from trustpipe.storage.s3 import S3Backend

        backend = S3Backend(bucket="test-bucket")
        with pytest.raises(ImportError, match="boto3"):
            backend._get_client()


def test_s3_backend_interface():
    """S3Backend implements all StorageBackend methods."""
    from trustpipe.storage.base import StorageBackend
    from trustpipe.storage.s3 import S3Backend

    assert issubclass(S3Backend, StorageBackend)

    backend = S3Backend(bucket="test-bucket")
    required = [
        "initialize",
        "save_provenance_record",
        "load_provenance_record",
        "query_provenance_by_name",
        "save_merkle_hash",
        "load_merkle_hashes",
        "save_trust_score",
        "load_latest_trust_score",
        "save_compliance_report",
        "get_record_count",
        "get_latest_records",
    ]
    for method in required:
        assert hasattr(backend, method), f"Missing method: {method}"


def test_s3_key_generation():
    """Key paths should follow the expected structure."""
    from trustpipe.storage.s3 import S3Backend

    backend = S3Backend(bucket="mybucket", prefix="tp")
    assert backend._key("default", "provenance", "abc.json") == "tp/default/provenance/abc.json"
    assert backend._key("prod", "merkle", "00000001.json") == "tp/prod/merkle/00000001.json"
