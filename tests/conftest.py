"""Shared test fixtures."""

import pytest

from trustpipe import TrustPipe
from trustpipe.storage.sqlite import SQLiteBackend


@pytest.fixture
def tp(tmp_path):
    """Fresh TrustPipe instance with ephemeral SQLite DB."""
    db = tmp_path / "test.db"
    return TrustPipe(db_path=db)


@pytest.fixture
def storage(tmp_path):
    """Fresh SQLite backend for direct storage testing."""
    backend = SQLiteBackend(path=tmp_path / "test.db")
    backend.initialize()
    return backend
