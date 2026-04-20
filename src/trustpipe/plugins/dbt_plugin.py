"""dbt plugin — auto-tracks dbt model runs via manifest.json parsing.

Usage:
    # In your dbt project, add to dbt_project.yml:
    #   on-run-end:
    #     - "{{ trustpipe_track(results) }}"
    #
    # Or use the CLI after dbt run:
    #   trustpipe dbt-import --manifest target/manifest.json --results target/run_results.json

    # Programmatic usage:
    from trustpipe import TrustPipe
    from trustpipe.plugins.dbt_plugin import DbtPlugin

    tp = TrustPipe()
    dbt = DbtPlugin(tp)
    dbt.import_manifest("target/manifest.json")
    dbt.import_run_results("target/run_results.json")
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from trustpipe.core.engine import TrustPipe
from trustpipe.provenance.record import ProvenanceRecord


class DbtPlugin:
    """Tracks dbt models, sources, and test results as provenance records."""

    def __init__(self, tp: TrustPipe) -> None:
        self._tp = tp

    def import_manifest(self, manifest_path: str | Path) -> list[ProvenanceRecord]:
        """Import dbt manifest.json to build provenance graph.

        Reads:
        - nodes (models, seeds, snapshots)
        - sources
        - parent/child relationships (depends_on)

        Returns list of created provenance records.
        """
        path = Path(manifest_path)
        if not path.exists():
            raise FileNotFoundError(f"Manifest not found: {path}")

        manifest = json.loads(path.read_text())
        records: list[ProvenanceRecord] = []
        id_map: dict[str, str] = {}  # dbt unique_id → trustpipe record_id

        # Track sources first (they have no parents)
        for unique_id, source in manifest.get("sources", {}).items():
            record = self._tp.track(
                {
                    "row_count": source.get("loaded_at_field"),
                    "columns": len(source.get("columns", {})),
                    "column_names": list(source.get("columns", {}).keys()),
                },
                name=source.get("name", unique_id),
                source=f"dbt://source/{source.get('source_name', '')}/{source.get('name', '')}",
                tags=["dbt", "source"],
                metadata={
                    "dbt_unique_id": unique_id,
                    "database": source.get("database", ""),
                    "schema": source.get("schema", ""),
                    "description": source.get("description", ""),
                },
            )
            id_map[unique_id] = record.id
            records.append(record)

        # Track nodes (models, seeds, snapshots) in dependency order
        nodes = manifest.get("nodes", {})
        processed: set[str] = set()

        def process_node(unique_id: str) -> Optional[ProvenanceRecord]:
            if unique_id in processed:
                return None
            if unique_id not in nodes:
                return None

            node = nodes[unique_id]

            # Process parents first
            parent_ids: list[str] = []
            for dep in node.get("depends_on", {}).get("nodes", []):
                if dep in id_map:
                    parent_ids.append(id_map[dep])
                elif dep in nodes and dep not in processed:
                    parent_rec = process_node(dep)
                    if parent_rec:
                        parent_ids.append(parent_rec.id)

            processed.add(unique_id)

            record = self._tp.track(
                {
                    "columns": len(node.get("columns", {})),
                    "column_names": list(node.get("columns", {}).keys()),
                },
                name=node.get("name", unique_id),
                source=f"dbt://{node.get('resource_type', 'model')}/{node.get('schema', '')}/{node.get('name', '')}",
                parents=parent_ids if parent_ids else None,
                tags=["dbt", node.get("resource_type", "model")],
                metadata={
                    "dbt_unique_id": unique_id,
                    "resource_type": node.get("resource_type", ""),
                    "database": node.get("database", ""),
                    "schema": node.get("schema", ""),
                    "description": node.get("description", ""),
                    "materialized": node.get("config", {}).get("materialized", ""),
                    "tags": node.get("tags", []),
                },
            )
            id_map[unique_id] = record.id
            records.append(record)
            return record

        for unique_id in nodes:
            process_node(unique_id)

        return records

    def import_run_results(
        self,
        results_path: str | Path,
        manifest_path: Optional[str | Path] = None,
    ) -> list[dict[str, Any]]:
        """Import dbt run_results.json to record execution metadata.

        Attaches execution timing, row counts, and status to
        existing provenance records.

        Returns list of result summaries.
        """
        path = Path(results_path)
        if not path.exists():
            raise FileNotFoundError(f"Run results not found: {path}")

        results = json.loads(path.read_text())
        summaries: list[dict[str, Any]] = []

        for result in results.get("results", []):
            unique_id = result.get("unique_id", "")
            status = result.get("status", "unknown")
            execution_time = result.get("execution_time", 0)
            rows_affected = result.get("adapter_response", {}).get("rows_affected")

            # Try to find matching provenance record by dbt unique_id
            # We search by checking metadata
            name = unique_id.split(".")[-1] if "." in unique_id else unique_id
            chain = self._tp.trace(name)

            summary = {
                "unique_id": unique_id,
                "name": name,
                "status": status,
                "execution_time": execution_time,
                "rows_affected": rows_affected,
                "tracked": len(chain) > 0,
            }

            # Update metadata on the latest record if found
            if chain:
                latest = chain[-1]
                updated_meta = dict(latest.metadata)
                updated_meta["dbt_run_status"] = status
                updated_meta["dbt_execution_time"] = execution_time
                if rows_affected is not None:
                    updated_meta["dbt_rows_affected"] = rows_affected

                # Track a new version with run results
                self._tp.track(
                    {"row_count": rows_affected, "columns": latest.column_count},
                    name=name,
                    parent=latest.id,
                    tags=["dbt", "run-result"],
                    metadata=updated_meta,
                )
                summary["tracked"] = True

            summaries.append(summary)

        return summaries
