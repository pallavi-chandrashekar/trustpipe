"""Tests for Airflow plugin (decorator-based, no Airflow dependency needed)."""

from trustpipe.plugins.airflow_plugin import trustpipe_task


def test_trustpipe_task_decorator(tp):
    """Test that the decorator tracks output provenance."""

    @trustpipe_task(tp, name="etl_output")
    def my_transform(data):
        return {"rows": len(data), "processed": True}

    result = my_transform([1, 2, 3, 4, 5])
    assert result == {"rows": 5, "processed": True}

    # Check provenance was recorded
    chain = tp.trace("etl_output")
    assert len(chain) == 1


def test_trustpipe_task_with_inputs(tp):
    """Test parent linkage from input dataset names."""
    # First, track an input dataset
    tp.track({"rows": 100}, name="raw_input", source="s3://raw")

    @trustpipe_task(tp, name="transformed", inputs=["raw_input"])
    def transform(data):
        return {"rows": 80}

    transform(None)

    chain = tp.trace("transformed")
    assert len(chain) == 1
    assert len(chain[0].parent_ids) == 1  # linked to raw_input


def test_trustpipe_task_default_name(tp):
    """Without explicit name, uses function name."""

    @trustpipe_task(tp)
    def my_cool_function():
        return {"rows": 50}

    my_cool_function()

    chain = tp.trace("my_cool_function")
    assert len(chain) == 1


def test_trustpipe_task_never_breaks_function(tp):
    """Decorator should never break the wrapped function."""

    @trustpipe_task(tp, name="safe_task")
    def important_function(x):
        return x * 2

    assert important_function(5) == 10
