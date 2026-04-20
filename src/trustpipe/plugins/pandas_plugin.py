"""Pandas plugin — auto-tracks all pd.read_* and df.to_* operations."""

from __future__ import annotations

import functools
from typing import Any

from trustpipe.plugins.base import TrustPipePlugin


class PandasPlugin(TrustPipePlugin):
    """Auto-tracks Pandas read/write operations.

    Usage:
        tp = TrustPipe()
        tp.pandas()  # activates — that's it

        df = pd.read_csv("data.csv")     # automatically tracked
        df.to_parquet("output.parquet")   # automatically tracked
    """

    _original_readers: dict[str, Any] = {}
    _original_writers: dict[str, Any] = {}
    _active: bool = False

    def activate(self) -> None:
        if self._active:
            return

        import pandas as pd

        readers = ["read_csv", "read_parquet", "read_json", "read_excel"]
        for name in readers:
            original = getattr(pd, name, None)
            if original and name not in self._original_readers:
                self._original_readers[name] = original
                setattr(pd, name, self._wrap_reader(original, name))

        writers = ["to_csv", "to_parquet", "to_json"]
        for name in writers:
            original = getattr(pd.DataFrame, name, None)
            if original and name not in self._original_writers:
                self._original_writers[name] = original
                setattr(pd.DataFrame, name, self._wrap_writer(original, name))

        self._active = True

    def deactivate(self) -> None:
        if not self._active:
            return

        import pandas as pd

        for name, original in self._original_readers.items():
            setattr(pd, name, original)
        for name, original in self._original_writers.items():
            setattr(pd.DataFrame, name, original)

        self._original_readers.clear()
        self._original_writers.clear()
        self._active = False

    def _wrap_reader(self, original: Any, reader_name: str) -> Any:
        plugin = self

        @functools.wraps(original)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = original(*args, **kwargs)
            source = str(args[0]) if args else str(kwargs.get("filepath_or_buffer", "unknown"))
            try:
                plugin.on_read(source=source, data=result, metadata={"reader": reader_name})
            except Exception:
                pass  # never break user's code
            return result

        return wrapper

    def _wrap_writer(self, original: Any, writer_name: str) -> Any:
        plugin = self

        @functools.wraps(original)
        def wrapper(df_self: Any, *args: Any, **kwargs: Any) -> Any:
            result = original(df_self, *args, **kwargs)
            dest = str(args[0]) if args else str(kwargs.get("path_or_buf", "unknown"))
            try:
                plugin.on_write(destination=dest, data=df_self, metadata={"writer": writer_name})
            except Exception:
                pass  # never break user's code
            return result

        return wrapper
