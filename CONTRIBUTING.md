# Contributing to TrustPipe

Thank you for your interest in contributing to TrustPipe! This guide will help you get started.

## Development Setup

```bash
# Clone the repo
git clone https://github.com/pallavi-chandrashekar/trustpipe.git
cd trustpipe

# Install in development mode (all optional dependencies)
pip install -e ".[dev]"

# Verify setup
make test
make lint
```

## Running Tests

```bash
# Full test suite (118 tests)
make test

# Unit tests only (fast)
make test-quick

# Specific test file
pytest tests/unit/test_trust_scorer.py -v

# With coverage
pytest tests/ --cov=trustpipe --cov-report=html
```

## Code Quality

```bash
# Lint check
make lint

# Auto-format
make format

# Both use ruff (config in pyproject.toml)
```

### Style Guidelines

- **Line length:** 120 characters max
- **Python version:** 3.10+ (use `from __future__ import annotations`)
- **Type hints:** Required for all public functions
- **Docstrings:** Required for all public classes and functions
- **Imports:** Sorted by ruff (isort-compatible)

## Project Structure

```
src/trustpipe/
├── core/           # Engine, config, exceptions, federation
├── provenance/     # Merkle chain, records, lineage
├── trust/          # Scorer, dimensions, drift, poisoning
├── compliance/     # Reporter, EU AI Act, templates
├── storage/        # SQLite, PostgreSQL, S3 backends
├── plugins/        # Pandas, Spark, Airflow, dbt, Kafka
├── cli/            # Click commands, formatters
├── api/            # FastAPI REST server
├── dashboard/      # Plotly Dash web UI
├── alerts/         # Webhook, Slack integrations
└── llm/            # Optional LLM providers
```

## How to Contribute

### Bug Reports

Open an issue with:
- Python version and OS
- Minimal code to reproduce
- Expected vs actual behavior
- Full error traceback

### Feature Requests

Open an issue describing:
- The use case / problem
- Proposed solution
- Alternatives considered

### Pull Requests

1. Fork the repo and create a branch from `main`
2. Make your changes
3. Add tests for new functionality
4. Ensure all tests pass: `make test`
5. Ensure lint passes: `make lint`
6. Write a clear PR description

#### PR Checklist

- [ ] Tests added/updated
- [ ] Lint passes (`make lint`)
- [ ] All tests pass (`make test`)
- [ ] Docstrings for new public APIs
- [ ] Example updated if user-facing behavior changed

### Adding a New Plugin

1. Create `src/trustpipe/plugins/your_plugin.py`
2. Extend `TrustPipePlugin` base class (see `plugins/base.py`)
3. Implement `activate()` and `deactivate()`
4. Add tests in `tests/unit/test_your_plugin.py`
5. Add optional dependency in `pyproject.toml`
6. Add example in `examples/`

### Adding a New Storage Backend

1. Create `src/trustpipe/storage/your_backend.py`
2. Implement all methods from `StorageBackend` ABC (see `storage/base.py`)
3. Add tests in `tests/unit/test_your_backend.py`
4. Add optional dependency in `pyproject.toml`

## Key Design Principles

When contributing, keep these in mind:

1. **Zero-config start** — new features should work with sensible defaults
2. **Never store raw data** — only fingerprints, hashes, and statistics
3. **Lazy imports** — optional dependencies imported inside functions, wrapped in try/except
4. **Never break user code** — plugins must catch all exceptions internally
5. **Graceful degradation** — missing optional deps return neutral values, never crash
6. **Tests required** — every feature needs tests, every bug fix needs a regression test

## Questions?

Open an issue or reach out. We're happy to help!
