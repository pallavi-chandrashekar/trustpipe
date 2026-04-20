"""Tests for the CI/CD trust gate CLI command."""

from click.testing import CliRunner

from trustpipe import TrustPipe
from trustpipe.cli.main import cli


def test_gate_pass(tmp_path):
    # Seed data
    tp = TrustPipe(db_path=tmp_path / "gate.db")
    tp.track({"rows": 1000, "columns": 5}, name="good_data", source="s3://test")

    runner = CliRunner()
    result = runner.invoke(cli, [
        "--db", str(tmp_path / "gate.db"),
        "gate", "good_data", "--threshold", "30",
    ])
    assert result.exit_code == 0
    assert "PASS" in result.output


def test_gate_fail_high_threshold(tmp_path):
    tp = TrustPipe(db_path=tmp_path / "gate.db")
    tp.track({"rows": 10}, name="test_data")

    runner = CliRunner()
    result = runner.invoke(cli, [
        "--db", str(tmp_path / "gate.db"),
        "gate", "test_data", "--threshold", "99",
    ])
    assert result.exit_code == 1
    assert "FAIL" in result.output


def test_gate_no_records(tmp_path):
    runner = CliRunner()
    result = runner.invoke(cli, [
        "--db", str(tmp_path / "gate.db"),
        "gate", "nonexistent",
    ])
    assert result.exit_code == 1
    assert "FAIL" in result.output
