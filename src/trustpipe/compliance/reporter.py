"""ComplianceReporter — generate audit and regulatory compliance reports."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from trustpipe._version import __version__
from trustpipe.compliance.eu_ai_act import (
    assess_compliance_gaps,
    build_article10_metadata,
)
from trustpipe.core.config import TrustPipeConfig
from trustpipe.storage.base import StorageBackend

TEMPLATES_DIR = Path(__file__).parent / "templates"

REGULATION_TEMPLATES = {
    "eu-ai-act-article-10": "article10.md.j2",
    "datacard": "datacard.md.j2",
    "audit-log": "audit_log.md.j2",
}


class ComplianceReporter:
    """Generates compliance reports from provenance + trust data."""

    def __init__(
        self,
        storage: StorageBackend,
        config: TrustPipeConfig | None = None,
    ) -> None:
        self._storage = storage
        self._config = config or TrustPipeConfig()
        self._env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=select_autoescape(default=False),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate(
        self,
        dataset_name: str,
        *,
        regulation: str = "eu-ai-act-article-10",
        project: str = "default",
        output_format: str = "markdown",
        user_metadata: dict[str, Any] | None = None,
        chain_root: str | None = None,
    ) -> str:
        """Generate a compliance report for a named dataset.

        Args:
            dataset_name: The dataset to report on (must have provenance).
            regulation: Target regulation template.
            project: Project namespace.
            output_format: "markdown", "json", or "html".
            user_metadata: User-supplied fields (intended_use, bias info, etc.).
            chain_root: Current Merkle chain root hash.

        Returns:
            The report content as a string.
        """
        # Gather provenance records
        records = self._storage.query_provenance_by_name(dataset_name, project)

        # Gather trust score
        trust_score = self._storage.load_latest_trust_score(dataset_name, project)

        # Build verification result
        verification = {"integrity": "OK"} if chain_root else {"integrity": "UNVERIFIED"}

        # Build Article 10 metadata
        metadata = build_article10_metadata(
            records=records,
            trust_score=trust_score,
            verification_result=verification,
            user_metadata=user_metadata,
        )

        # Run gap analysis
        gaps = assess_compliance_gaps(metadata)

        if output_format == "json":
            import json

            return json.dumps(
                {
                    "dataset_name": dataset_name,
                    "regulation": regulation,
                    "metadata": metadata.model_dump(),
                    "gaps": [g.model_dump() for g in gaps],
                },
                indent=2,
                default=str,
            )

        # Render template
        template_file = REGULATION_TEMPLATES.get(regulation)
        if not template_file:
            available = ", ".join(REGULATION_TEMPLATES.keys())
            raise ValueError(f"Unknown regulation '{regulation}'. Available: {available}")

        template = self._env.get_template(template_file)
        content = template.render(
            dataset_name=dataset_name,
            metadata=metadata,
            gaps=gaps,
            chain_root=chain_root,
            version=__version__,
        )

        return content
