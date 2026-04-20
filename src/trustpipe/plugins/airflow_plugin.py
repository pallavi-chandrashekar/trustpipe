"""Airflow plugin — @trustpipe_task decorator for provenance tracking.

Usage in an Airflow DAG:
    from trustpipe import TrustPipe
    from trustpipe.plugins.airflow_plugin import trustpipe_task

    tp = TrustPipe()

    @trustpipe_task(tp, name="transform_customers", inputs=["raw_customers"])
    @task
    def transform_customers(raw_df):
        return processed_df
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from trustpipe.core.engine import TrustPipe


def trustpipe_task(
    tp: TrustPipe,
    *,
    name: str | None = None,
    inputs: list[str] | None = None,
    outputs: list[str] | None = None,
    tags: list[str] | None = None,
) -> Callable:
    """Decorator that wraps an Airflow @task with provenance tracking.

    Args:
        tp: TrustPipe instance.
        name: Provenance name for the output. Defaults to function name.
        inputs: Names of input datasets (used to find parent record IDs).
        outputs: Not used currently — reserved for multi-output tasks.
        tags: Tags to attach to the provenance record.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = func(*args, **kwargs)

            resolved_name = name or func.__name__

            # Find parent IDs from input dataset names
            parent_ids: list[str] = []
            if inputs:
                for inp in inputs:
                    chain = tp.trace(inp)
                    if chain:
                        parent_ids.append(chain[-1].id)

            try:
                tp.track(
                    result,
                    name=resolved_name,
                    parents=parent_ids if parent_ids else None,
                    tags=tags,
                    metadata={
                        "airflow_task": func.__name__,
                        "framework": "airflow",
                    },
                )
            except Exception:
                pass  # never break the DAG

            return result

        return wrapper

    return decorator


class AirflowPlugin:
    """Alternative: class-based plugin that wraps a full DAG.

    Usage:
        tp = TrustPipe()
        airflow = AirflowPlugin(tp)

        @airflow.track(name="etl_output", inputs=["raw_data"])
        @task
        def my_task(data):
            return transformed_data
    """

    def __init__(self, tp: TrustPipe) -> None:
        self._tp = tp

    def track(
        self,
        *,
        name: str | None = None,
        inputs: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> Callable:
        """Decorator for tracking a single Airflow task."""
        return trustpipe_task(self._tp, name=name, inputs=inputs, tags=tags)
