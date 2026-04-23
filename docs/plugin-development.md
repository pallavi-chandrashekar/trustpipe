# Plugin Development Guide

Build custom TrustPipe integrations for any data framework.

## Plugin Architecture

All plugins extend `TrustPipePlugin`:

```python
from trustpipe.plugins.base import TrustPipePlugin

class MyPlugin(TrustPipePlugin):
    def activate(self) -> None:
        """Install hooks into your framework."""
        ...

    def deactivate(self) -> None:
        """Remove hooks. Clean teardown."""
        ...
```

The base class provides `on_read()` and `on_write()` methods that call `tp.track()` with appropriate metadata.

## Creating a Plugin

### Step 1: Create the plugin file

```python
# src/trustpipe/plugins/my_framework_plugin.py
from __future__ import annotations
from typing import Any
from trustpipe.plugins.base import TrustPipePlugin


class MyFrameworkPlugin(TrustPipePlugin):
    def __init__(self, tp, framework_client, **kwargs):
        super().__init__(tp, **kwargs)
        self._client = framework_client
        self._original_method = None

    def activate(self) -> None:
        # Save original method
        self._original_method = self._client.read_data

        plugin = self

        def tracked_read(*args, **kwargs):
            result = plugin._original_method(*args, **kwargs)
            try:
                source = str(args[0]) if args else "unknown"
                plugin.on_read(source=source, data=result)
            except Exception:
                pass  # NEVER break user code
            return result

        self._client.read_data = tracked_read

    def deactivate(self) -> None:
        if self._original_method:
            self._client.read_data = self._original_method
            self._original_method = None
```

### Step 2: Add a convenience method to TrustPipe

```python
# In src/trustpipe/core/engine.py, add:
def my_framework(self, client):
    from trustpipe.plugins.my_framework_plugin import MyFrameworkPlugin
    plugin = MyFrameworkPlugin(self, client)
    plugin.activate()
    return plugin
```

### Step 3: Add tests

```python
# tests/unit/test_my_framework_plugin.py
from unittest.mock import MagicMock

def test_plugin_tracks_reads(tp):
    mock_client = MagicMock()
    mock_client.read_data.return_value = {"rows": 100}

    from trustpipe.plugins.my_framework_plugin import MyFrameworkPlugin
    plugin = MyFrameworkPlugin(tp, mock_client)
    plugin.activate()

    result = mock_client.read_data("s3://data.csv")
    chain = tp.trace("data")
    assert len(chain) >= 1

    plugin.deactivate()
```

### Step 4: Add optional dependency

```toml
# In pyproject.toml:
[project.optional-dependencies]
my_framework = ["my-framework-sdk>=1.0"]
```

## Key Rules

1. **Never break user code** — wrap all tracking in `try/except Exception: pass`
2. **Lazy imports** — import the framework inside `activate()`, not at module level
3. **Clean deactivation** — `deactivate()` must restore original behavior exactly
4. **Infer names** — use `_infer_name(path)` from the base class to derive dataset names from paths
5. **Include metadata** — pass `metadata={"framework": "my_framework"}` for traceability

## Existing Plugins as Reference

| Plugin | Pattern | File |
|--------|---------|------|
| **Pandas** | Monkey-patching `pd.read_csv` etc. | `plugins/pandas_plugin.py` |
| **Spark** | Wrapping `DataFrameReader.load` | `plugins/spark_plugin.py` |
| **Airflow** | Function decorator | `plugins/airflow_plugin.py` |
| **dbt** | Manifest/results JSON parsing | `plugins/dbt_plugin.py` |
| **Kafka** | Consumer/Producer wrapper | `plugins/kafka_plugin.py` |
