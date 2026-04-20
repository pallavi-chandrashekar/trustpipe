"""Tests for Pandas auto-tracking plugin."""

import pandas as pd


def test_pandas_plugin_tracks_read_csv(tp, tmp_path):
    # Create a test CSV
    csv_path = tmp_path / "data.csv"
    pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]}).to_csv(csv_path, index=False)

    # Activate plugin
    plugin = tp.pandas()

    try:
        # Read should be auto-tracked
        df = pd.read_csv(csv_path)
        assert len(df) == 3

        # Check provenance was recorded
        records = tp.trace("data")
        assert len(records) == 1
        assert records[0].row_count == 3
        assert records[0].column_names == ["a", "b"]
    finally:
        plugin.deactivate()


def test_pandas_plugin_tracks_write_csv(tp, tmp_path):
    output_path = tmp_path / "output.csv"

    plugin = tp.pandas()

    try:
        df = pd.DataFrame({"x": [10, 20], "y": [30, 40]})
        df.to_csv(output_path, index=False)

        # Check provenance was recorded for the write
        records = tp.trace("output")
        assert len(records) == 1
        assert records[0].row_count == 2
    finally:
        plugin.deactivate()


def test_pandas_plugin_deactivation(tp, tmp_path):
    csv_path = tmp_path / "test.csv"
    pd.DataFrame({"a": [1]}).to_csv(csv_path, index=False)

    plugin = tp.pandas()
    plugin.deactivate()

    # After deactivation, reads should NOT be tracked
    pd.read_csv(csv_path)
    records = tp.trace("test")
    assert len(records) == 0


def test_pandas_plugin_never_breaks_user_code(tp):
    """Plugin errors should never break the user's pandas operations."""
    plugin = tp.pandas()

    try:
        # This should work even if tracking fails internally
        df = pd.DataFrame({"a": [1, 2, 3]})
        assert len(df) == 3
    finally:
        plugin.deactivate()
