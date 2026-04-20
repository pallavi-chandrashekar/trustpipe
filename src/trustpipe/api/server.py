"""TrustPipe REST API — FastAPI application.

Launch: trustpipe serve --port 8000
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from trustpipe._version import __version__
from trustpipe.core.engine import TrustPipe


# ── Request/Response Models ──────────────────────────────────

class TrackRequest(BaseModel):
    name: str
    source: Optional[str] = None
    parent: Optional[str] = None
    parents: Optional[list[str]] = None
    metadata: Optional[dict[str, Any]] = None
    tags: Optional[list[str]] = None
    data: dict[str, Any] = Field(default_factory=dict, description="Data stats (row_count, columns, etc.)")


class ScoreRequest(BaseModel):
    name: str
    checks: Optional[list[str]] = None


class ComplyRequest(BaseModel):
    regulation: str = "eu-ai-act-article-10"
    output_format: str = "markdown"
    user_metadata: Optional[dict[str, Any]] = None


# ── API Factory ──────────────────────────────────────────────

def create_api(tp: TrustPipe) -> FastAPI:
    """Create the FastAPI application."""

    app = FastAPI(
        title="TrustPipe API",
        description="AI Data Supply Chain Trust & Provenance Platform",
        version=__version__,
    )

    @app.get("/")
    async def root():
        return {"name": "TrustPipe", "version": __version__}

    @app.get("/status")
    async def status():
        return tp.status()

    # ── Provenance ────────────────────────────────────────

    @app.post("/track")
    async def track(req: TrackRequest):
        record = tp.track(
            req.data,
            name=req.name,
            source=req.source,
            parent=req.parent,
            parents=req.parents,
            metadata=req.metadata,
            tags=req.tags,
        )
        return record.to_dict()

    @app.get("/trace/{name}")
    async def trace(name: str):
        chain = tp.trace(name)
        if not chain:
            raise HTTPException(404, f"No provenance records found for '{name}'")
        return [r.to_dict() for r in chain]

    @app.get("/lineage/{name}")
    async def lineage(name: str):
        graph = tp.lineage(name)
        if not graph:
            raise HTTPException(404, f"No lineage found for '{name}'")
        return {"tree": graph.to_tree_string()}

    @app.get("/verify")
    async def verify(record_id: Optional[str] = None):
        return tp.verify(record_id)

    # ── Trust ─────────────────────────────────────────────

    @app.get("/score/{name}")
    async def score(name: str, checks: Optional[str] = None):
        chain = tp.trace(name)
        if not chain:
            raise HTTPException(404, f"No provenance records found for '{name}'")
        latest = chain[-1]
        check_list = checks.split(",") if checks else None
        result = tp.score(
            latest.statistical_summary or {"row_count": latest.row_count},
            name=name,
            checks=check_list,
        )
        return result.to_dict()

    @app.post("/score")
    async def score_data(req: ScoreRequest):
        """Score with inline data stats."""
        chain = tp.trace(req.name)
        data = {}
        if chain:
            latest = chain[-1]
            data = latest.statistical_summary or {"row_count": latest.row_count}
        result = tp.score(data, name=req.name, checks=req.checks)
        return result.to_dict()

    # ── Compliance ────────────────────────────────────────

    @app.get("/comply/{name}")
    async def comply_get(
        name: str,
        regulation: str = "eu-ai-act-article-10",
        output_format: str = "json",
    ):
        chain = tp.trace(name)
        if not chain:
            raise HTTPException(404, f"No provenance records found for '{name}'")
        content = tp.comply(name, regulation=regulation, output_format=output_format)
        if output_format == "json":
            import json
            return json.loads(content)
        return {"content": content, "format": output_format}

    @app.post("/comply/{name}")
    async def comply_post(name: str, req: ComplyRequest):
        chain = tp.trace(name)
        if not chain:
            raise HTTPException(404, f"No provenance records found for '{name}'")
        content = tp.comply(
            name,
            regulation=req.regulation,
            output_format=req.output_format,
            user_metadata=req.user_metadata,
        )
        if req.output_format == "json":
            import json
            return json.loads(content)
        return {"content": content, "format": req.output_format}

    # ── Export ────────────────────────────────────────────

    @app.get("/export")
    async def export_records(limit: int = 1000):
        records = tp._storage.get_latest_records(tp.project, limit=limit)
        return [r.to_dict() for r in records]

    return app


def run_api(
    tp: TrustPipe,
    host: str = "127.0.0.1",
    port: int = 8000,
) -> None:
    """Launch the API server."""
    import uvicorn
    app = create_api(tp)
    uvicorn.run(app, host=host, port=port)
