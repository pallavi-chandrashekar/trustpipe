"""Base class for all TrustPipe framework plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import PurePosixPath
from typing import Any, Optional

from trustpipe.core.engine import TrustPipe
from trustpipe.provenance.record import ProvenanceRecord


class TrustPipePlugin(ABC):
    """Base class for framework integrations.

    Plugins intercept data read/write events in their framework
    and call TrustPipe.track() automatically.
    """

    def __init__(self, tp: TrustPipe, **kwargs: Any) -> None:
        self._tp = tp
        self._config = kwargs

    @abstractmethod
    def activate(self) -> None:
        """Install hooks/listeners into the target framework."""
        ...

    @abstractmethod
    def deactivate(self) -> None:
        """Remove hooks/listeners. Clean teardown."""
        ...

    def on_read(
        self,
        source: str,
        data: Any,
        *,
        name: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> ProvenanceRecord:
        resolved_name = name or self._infer_name(source)
        return self._tp.track(data, name=resolved_name, source=source, metadata=metadata)

    def on_write(
        self,
        destination: str,
        data: Any,
        *,
        name: Optional[str] = None,
        parents: Optional[list[str]] = None,
        metadata: Optional[dict] = None,
    ) -> ProvenanceRecord:
        resolved_name = name or self._infer_name(destination)
        return self._tp.track(
            data, name=resolved_name, source=destination, parents=parents, metadata=metadata
        )

    @staticmethod
    def _infer_name(path: str) -> str:
        """Best-effort name inference from a path/URI."""
        cleaned = path.split("?")[0].rstrip("/")
        return PurePosixPath(cleaned).stem or "unknown"
