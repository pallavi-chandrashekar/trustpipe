"""Tests for PostgreSQL backend — uses mocked psycopg to avoid real DB dependency."""

import pytest
from unittest.mock import MagicMock, patch


def test_postgres_import_error():
    """PostgresBackend should raise helpful error if psycopg not installed."""
    with patch.dict("sys.modules", {"psycopg": None}):
        from trustpipe.storage.postgres import PostgresBackend
        backend = PostgresBackend("postgresql://localhost/test")
        with pytest.raises(ImportError, match="psycopg"):
            backend._get_conn()


def test_postgres_backend_interface():
    """PostgresBackend implements all StorageBackend methods."""
    from trustpipe.storage.postgres import PostgresBackend
    from trustpipe.storage.base import StorageBackend
    assert issubclass(PostgresBackend, StorageBackend)

    # Check all abstract methods are implemented
    backend = PostgresBackend("postgresql://localhost/test")
    required = [
        "initialize", "save_provenance_record", "load_provenance_record",
        "query_provenance_by_name", "save_merkle_hash", "load_merkle_hashes",
        "save_trust_score", "load_latest_trust_score", "save_compliance_report",
        "get_record_count", "get_latest_records",
    ]
    for method in required:
        assert hasattr(backend, method), f"Missing method: {method}"
