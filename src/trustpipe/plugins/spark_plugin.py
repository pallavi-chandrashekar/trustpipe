"""Spark plugin — auto-tracks Spark read/write operations via SparkListener.

Usage:
    from trustpipe import TrustPipe
    tp = TrustPipe()
    tp.spark(spark_session)  # one line, attaches listener

    # All spark.read and df.write operations are now auto-tracked
"""

from __future__ import annotations

from typing import Any

from trustpipe.plugins.base import TrustPipePlugin


class SparkPlugin(TrustPipePlugin):
    """Auto-tracks Spark read/write operations via SparkListener.

    Requires pyspark. Optional pyspark-spy for richer event data.
    Falls back to wrapping DataFrameReader/DataFrameWriter if
    SparkListener is unavailable.
    """

    def __init__(self, tp: Any, spark_session: Any, **kwargs: Any) -> None:
        super().__init__(tp, **kwargs)
        self._spark = spark_session
        self._original_load: Any | None = None
        self._original_save: Any | None = None

    def activate(self) -> None:
        """Wrap Spark's DataFrameReader.load and DataFrameWriter.save."""
        from pyspark.sql import DataFrameReader, DataFrameWriter

        plugin = self

        # Wrap reader
        self._original_load = DataFrameReader.load

        def tracked_load(reader_self: Any, path: Any = None, **kwargs: Any) -> Any:
            result = plugin._original_load(reader_self, path, **kwargs)
            if path:
                try:
                    source = str(path)
                    row_count = result.count() if hasattr(result, "count") else None
                    schema_json = result.schema.jsonValue() if hasattr(result, "schema") else {}
                    plugin.on_read(
                        source=source,
                        data={"row_count": row_count, "schema": str(schema_json)},
                        metadata={"format": kwargs.get("format", "unknown"), "framework": "spark"},
                    )
                except Exception:
                    pass  # never break user's Spark job
            return result

        DataFrameReader.load = tracked_load

        # Wrap writer
        self._original_save = DataFrameWriter.save

        def tracked_save(writer_self: Any, path: Any = None, **kwargs: Any) -> None:
            plugin._original_save(writer_self, path, **kwargs)
            if path:
                try:
                    dest = str(path)
                    plugin.on_write(
                        destination=dest,
                        data={"framework": "spark"},
                        metadata={
                            "format": kwargs.get("format", "unknown"),
                            "mode": kwargs.get("mode", "default"),
                        },
                    )
                except Exception:
                    pass

        DataFrameWriter.save = tracked_save

    def deactivate(self) -> None:
        """Restore original Spark reader/writer methods."""
        if self._original_load:
            from pyspark.sql import DataFrameReader

            DataFrameReader.load = self._original_load
            self._original_load = None

        if self._original_save:
            from pyspark.sql import DataFrameWriter

            DataFrameWriter.save = self._original_save
            self._original_save = None
