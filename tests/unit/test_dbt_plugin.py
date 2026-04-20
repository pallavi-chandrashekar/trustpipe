"""Tests for dbt plugin."""

import json

import pytest

from trustpipe.plugins.dbt_plugin import DbtPlugin


@pytest.fixture
def sample_manifest(tmp_path):
    """Create a minimal dbt manifest.json for testing."""
    manifest = {
        "sources": {
            "source.myproject.raw.customers": {
                "name": "customers",
                "source_name": "raw",
                "database": "analytics",
                "schema": "raw",
                "description": "Raw customer data",
                "columns": {"id": {}, "name": {}, "email": {}},
            }
        },
        "nodes": {
            "model.myproject.stg_customers": {
                "name": "stg_customers",
                "resource_type": "model",
                "database": "analytics",
                "schema": "staging",
                "description": "Staged customers",
                "columns": {"id": {}, "name": {}, "email": {}, "created_at": {}},
                "depends_on": {"nodes": ["source.myproject.raw.customers"]},
                "config": {"materialized": "view"},
                "tags": [],
            },
            "model.myproject.dim_customers": {
                "name": "dim_customers",
                "resource_type": "model",
                "database": "analytics",
                "schema": "marts",
                "description": "Customer dimension",
                "columns": {"customer_id": {}, "full_name": {}, "is_active": {}},
                "depends_on": {"nodes": ["model.myproject.stg_customers"]},
                "config": {"materialized": "table"},
                "tags": ["marts"],
            },
        },
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    return path


@pytest.fixture
def sample_run_results(tmp_path):
    """Create a minimal dbt run_results.json for testing."""
    results = {
        "results": [
            {
                "unique_id": "model.myproject.stg_customers",
                "status": "success",
                "execution_time": 1.23,
                "adapter_response": {"rows_affected": 5000},
            },
            {
                "unique_id": "model.myproject.dim_customers",
                "status": "success",
                "execution_time": 2.45,
                "adapter_response": {"rows_affected": 4800},
            },
        ],
    }
    path = tmp_path / "run_results.json"
    path.write_text(json.dumps(results))
    return path


def test_import_manifest(tp, sample_manifest):
    dbt = DbtPlugin(tp)
    records = dbt.import_manifest(sample_manifest)

    # Should create records for 1 source + 2 models
    assert len(records) == 3

    # Source should be tracked
    source_chain = tp.trace("customers")
    assert len(source_chain) == 1
    assert "dbt" in source_chain[0].tags
    assert "source" in source_chain[0].tags

    # Models should have parent linkage
    stg_chain = tp.trace("stg_customers")
    assert len(stg_chain) == 1
    assert len(stg_chain[0].parent_ids) == 1  # depends on source

    dim_chain = tp.trace("dim_customers")
    assert len(dim_chain) == 1
    assert len(dim_chain[0].parent_ids) == 1  # depends on stg


def test_import_manifest_not_found(tp, tmp_path):
    dbt = DbtPlugin(tp)
    with pytest.raises(FileNotFoundError):
        dbt.import_manifest(tmp_path / "nonexistent.json")


def test_import_run_results(tp, sample_manifest, sample_run_results):
    dbt = DbtPlugin(tp)
    # First import manifest to create records
    dbt.import_manifest(sample_manifest)

    # Then import run results
    summaries = dbt.import_run_results(sample_run_results)
    assert len(summaries) == 2
    assert all(s["status"] == "success" for s in summaries)
    assert all(s["tracked"] for s in summaries)

    # stg_customers should now have 2 records (manifest + run result)
    stg_chain = tp.trace("stg_customers")
    assert len(stg_chain) == 2


def test_dbt_lineage_tree(tp, sample_manifest):
    """Verify dbt models create a proper lineage tree."""
    dbt = DbtPlugin(tp)
    dbt.import_manifest(sample_manifest)

    lineage = tp.lineage("dim_customers")
    assert lineage is not None
    tree_str = lineage.to_tree_string()
    assert "dim_customers" in tree_str
    assert "stg_customers" in tree_str
