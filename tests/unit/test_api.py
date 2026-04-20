"""Tests for the FastAPI REST API."""

import pytest
from fastapi.testclient import TestClient

from trustpipe import TrustPipe
from trustpipe.api.server import create_api


@pytest.fixture
def client(tmp_path):
    tp = TrustPipe(db_path=tmp_path / "api_test.db")
    app = create_api(tp)
    return TestClient(app), tp


def test_root(client):
    c, _ = client
    resp = c.get("/")
    assert resp.status_code == 200
    assert resp.json()["name"] == "TrustPipe"


def test_status_empty(client):
    c, _ = client
    resp = c.get("/status")
    assert resp.status_code == 200
    assert resp.json()["record_count"] == 0


def test_track_and_trace(client):
    c, _ = client
    # Track
    resp = c.post(
        "/track",
        json={
            "name": "test_data",
            "source": "s3://bucket/data.csv",
            "data": {"rows": 100, "columns": 5},
        },
    )
    assert resp.status_code == 200
    record = resp.json()
    assert record["name"] == "test_data"
    assert record["source"] == "s3://bucket/data.csv"

    # Trace
    resp = c.get("/trace/test_data")
    assert resp.status_code == 200
    chain = resp.json()
    assert len(chain) == 1
    assert chain[0]["name"] == "test_data"


def test_trace_404(client):
    c, _ = client
    resp = c.get("/trace/nonexistent")
    assert resp.status_code == 404


def test_verify(client):
    c, _ = client
    c.post("/track", json={"name": "a", "data": {"rows": 10}})
    c.post("/track", json={"name": "b", "data": {"rows": 20}})

    resp = c.get("/verify")
    assert resp.status_code == 200
    assert resp.json()["integrity"] == "OK"


def test_score_endpoint(client):
    c, tp = client
    # Track first
    tp.track({"rows": 100}, name="scored_data", source="s3://test")

    resp = c.get("/score/scored_data")
    assert resp.status_code == 200
    data = resp.json()
    assert 0 <= data["composite"] <= 100
    assert data["grade"] in ("A+", "A", "B", "C", "D", "F")


def test_comply_endpoint(client):
    c, tp = client
    tp.track({"rows": 100}, name="comply_data", source="s3://test")

    resp = c.get("/comply/comply_data?output_format=json")
    assert resp.status_code == 200
    data = resp.json()
    assert "dataset_name" in data
    assert "gaps" in data


def test_export(client):
    c, tp = client
    tp.track({"rows": 100}, name="export_data")

    resp = c.get("/export")
    assert resp.status_code == 200
    records = resp.json()
    assert len(records) == 1


def test_track_with_parent(client):
    c, _ = client
    # Track parent
    resp1 = c.post("/track", json={"name": "raw", "data": {"rows": 100}, "source": "s3://raw"})
    parent_id = resp1.json()["id"]

    # Track child
    resp2 = c.post("/track", json={"name": "clean", "data": {"rows": 80}, "parent": parent_id})
    assert resp2.status_code == 200
    assert parent_id in resp2.json()["parent_ids"]
