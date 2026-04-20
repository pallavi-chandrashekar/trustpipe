"""S3 storage backend — enterprise scale.

Requires: pip install trustpipe[s3]
Stores provenance records, trust scores, and compliance reports as JSON objects.

Structure:
  s3://bucket/trustpipe/{project}/provenance/{record_id}.json
  s3://bucket/trustpipe/{project}/merkle/{index}.json
  s3://bucket/trustpipe/{project}/trust/{score_id}.json
  s3://bucket/trustpipe/{project}/compliance/{report_id}.json
  s3://bucket/trustpipe/{project}/indexes/name/{name}.json  (list of record IDs)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from trustpipe.core.exceptions import StorageError
from trustpipe.provenance.record import ProvenanceRecord
from trustpipe.storage.base import StorageBackend


class S3Backend(StorageBackend):
    """S3 storage backend using boto3.

    Usage:
        from trustpipe.storage.s3 import S3Backend
        backend = S3Backend(bucket="my-bucket", prefix="trustpipe")
        tp = TrustPipe(storage=backend)
    """

    def __init__(
        self,
        bucket: str,
        prefix: str = "trustpipe",
        region: Optional[str] = None,
    ) -> None:
        self._bucket = bucket
        self._prefix = prefix
        self._region = region
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import boto3
            except ImportError:
                raise ImportError("S3 backend requires boto3: pip install trustpipe[s3]")
            kwargs = {}
            if self._region:
                kwargs["region_name"] = self._region
            self._client = boto3.client("s3", **kwargs)
        return self._client

    def _key(self, *parts: str) -> str:
        return "/".join([self._prefix] + list(parts))

    def _put_json(self, key: str, data: dict) -> None:
        self._get_client().put_object(
            Bucket=self._bucket, Key=key,
            Body=json.dumps(data, default=str).encode(),
            ContentType="application/json",
        )

    def _get_json(self, key: str) -> Optional[dict]:
        try:
            resp = self._get_client().get_object(Bucket=self._bucket, Key=key)
            return json.loads(resp["Body"].read().decode())
        except self._get_client().exceptions.NoSuchKey:
            return None
        except Exception:
            return None

    def _list_keys(self, prefix: str) -> list[str]:
        client = self._get_client()
        keys = []
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                keys.append(obj["Key"])
        return keys

    def initialize(self) -> None:
        # S3 doesn't need schema migration — just verify bucket access
        try:
            self._get_client().head_bucket(Bucket=self._bucket)
        except Exception as e:
            raise StorageError(f"Cannot access S3 bucket '{self._bucket}': {e}") from e

    # ── Provenance ────────────────────────────────────────────

    def save_provenance_record(self, record: ProvenanceRecord) -> None:
        key = self._key(record.project, "provenance", f"{record.id}.json")
        self._put_json(key, record.to_dict())

        # Update name index
        index_key = self._key(record.project, "indexes", "name", f"{record.name}.json")
        existing = self._get_json(index_key) or {"ids": []}
        existing["ids"].append(record.id)
        self._put_json(index_key, existing)

    def load_provenance_record(self, record_id: str) -> Optional[ProvenanceRecord]:
        # Try default project first, then scan
        for project in self._list_projects():
            key = self._key(project, "provenance", f"{record_id}.json")
            data = self._get_json(key)
            if data:
                return ProvenanceRecord.from_dict(data)
        return None

    def query_provenance_by_name(self, name: str, project: str = "default") -> list[ProvenanceRecord]:
        index_key = self._key(project, "indexes", "name", f"{name}.json")
        index_data = self._get_json(index_key)
        if not index_data:
            return []

        records = []
        for rid in index_data.get("ids", []):
            key = self._key(project, "provenance", f"{rid}.json")
            data = self._get_json(key)
            if data:
                records.append(ProvenanceRecord.from_dict(data))

        return sorted(records, key=lambda r: r.created_at)

    # ── Merkle ────────────────────────────────────────────────

    def save_merkle_hash(self, index: int, hash_value: str, project: str = "default") -> None:
        key = self._key(project, "merkle", f"{index:08d}.json")
        self._put_json(key, {"idx": index, "hash": hash_value})

    def load_merkle_hashes(self, project: str = "default") -> list[str]:
        prefix = self._key(project, "merkle") + "/"
        keys = sorted(self._list_keys(prefix))
        hashes = []
        for k in keys:
            data = self._get_json(k)
            if data:
                hashes.append(data["hash"])
        return hashes

    # ── Trust Scores ──────────────────────────────────────────

    def save_trust_score(self, score_data: dict) -> None:
        project = score_data.get("project", "default")
        key = self._key(project, "trust", f"{score_data['id']}.json")
        self._put_json(key, score_data)

        # Update dataset index
        dataset = score_data.get("dataset_name", "")
        if dataset:
            index_key = self._key(project, "indexes", "trust", f"{dataset}.json")
            existing = self._get_json(index_key) or {"ids": []}
            existing["ids"].append(score_data["id"])
            self._put_json(index_key, existing)

    def load_latest_trust_score(self, dataset_name: str, project: str = "default") -> Optional[dict]:
        index_key = self._key(project, "indexes", "trust", f"{dataset_name}.json")
        index_data = self._get_json(index_key)
        if not index_data or not index_data.get("ids"):
            return None

        # Get the last score ID
        latest_id = index_data["ids"][-1]
        key = self._key(project, "trust", f"{latest_id}.json")
        return self._get_json(key)

    # ── Compliance ────────────────────────────────────────────

    def save_compliance_report(self, report_data: dict) -> None:
        project = report_data.get("project", "default")
        key = self._key(project, "compliance", f"{report_data['id']}.json")
        self._put_json(key, report_data)

    # ── Stats ─────────────────────────────────────────────────

    def get_record_count(self, project: str = "default") -> int:
        prefix = self._key(project, "provenance") + "/"
        return len(self._list_keys(prefix))

    def get_latest_records(self, project: str = "default", limit: int = 10) -> list[ProvenanceRecord]:
        prefix = self._key(project, "provenance") + "/"
        keys = sorted(self._list_keys(prefix), reverse=True)[:limit]
        records = []
        for k in keys:
            data = self._get_json(k)
            if data:
                records.append(ProvenanceRecord.from_dict(data))
        return records

    def _list_projects(self) -> list[str]:
        """List all project namespaces in the bucket."""
        prefix = self._prefix + "/"
        client = self._get_client()
        resp = client.list_objects_v2(Bucket=self._bucket, Prefix=prefix, Delimiter="/")
        projects = []
        for cp in resp.get("CommonPrefixes", []):
            proj = cp["Prefix"].rstrip("/").split("/")[-1]
            projects.append(proj)
        return projects or ["default"]
