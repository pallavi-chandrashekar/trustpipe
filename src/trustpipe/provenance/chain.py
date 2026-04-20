"""ProvenanceChain — append-only provenance log backed by a Merkle tree.

The Merkle tree provides:
1. Tamper evidence — any modification to a historical record changes the root hash.
2. Efficient verification — O(log n) proof for any record.
3. Append-only guarantee — new records extend the tree, old records are never modified.

This is NOT blockchain. No distributed consensus, no mining, no tokens.
It is a Merkle hash tree — the same data structure git uses for commits.
"""

from __future__ import annotations

from trustpipe.core.exceptions import ProvenanceError
from trustpipe.provenance.merkle import MerkleTree
from trustpipe.provenance.record import ProvenanceRecord
from trustpipe.storage.base import StorageBackend


class ProvenanceChain:
    """Append-only provenance log with Merkle integrity verification."""

    def __init__(self, storage: StorageBackend, project: str = "default") -> None:
        self._storage = storage
        self._project = project
        self._tree = MerkleTree()

        # Rebuild tree from stored hashes on startup
        stored_hashes = self._storage.load_merkle_hashes(project)
        for h in stored_hashes:
            self._tree.add_leaf(h, do_hash=False)
        if stored_hashes:
            self._tree.make_tree()

    def append(self, record: ProvenanceRecord) -> ProvenanceRecord:
        """Append a record to the chain.

        1. Compute content hash for the record
        2. Record the current root as previous_root
        3. Add hash as new Merkle leaf
        4. Rebuild tree, capture new root
        5. Store record + merkle node
        """
        content_hash = record.content_hash()
        record.previous_root = self._tree.get_merkle_root() or ""
        record.merkle_index = len(self._tree.leaves)
        record.project = self._project

        self._tree.add_leaf(content_hash, do_hash=False)
        self._tree.make_tree()

        root = self._tree.get_merkle_root()
        if root is None:
            raise ProvenanceError("Failed to compute Merkle root after append")
        record.merkle_root = root

        self._storage.save_provenance_record(record)
        self._storage.save_merkle_hash(record.merkle_index, content_hash, self._project)

        return record

    def verify(self, record_id: str) -> bool:
        """Verify a record's integrity against the Merkle tree.

        Returns True if the record's content hash matches its
        position in the current tree.
        """
        record = self._storage.load_provenance_record(record_id)
        if not record:
            return False

        content_hash = record.content_hash()
        root = self._tree.get_merkle_root()
        if root is None:
            return False

        proof = self._tree.get_proof(record.merkle_index)
        return self._tree.validate_proof(proof, content_hash, root)

    def get_chain(self, name: str) -> list[ProvenanceRecord]:
        """Get all records for a named dataset, ordered by time."""
        return self._storage.query_provenance_by_name(name, self._project)

    def get_ancestors(self, record_id: str) -> list[ProvenanceRecord]:
        """Walk parent_ids recursively to find full ancestry (root-first)."""
        visited: set[str] = set()
        result: list[ProvenanceRecord] = []
        queue = [record_id]

        while queue:
            rid = queue.pop(0)
            if rid in visited:
                continue
            visited.add(rid)
            record = self._storage.load_provenance_record(rid)
            if record:
                result.append(record)
                queue.extend(record.parent_ids)

        return list(reversed(result))  # root-first order

    @property
    def root(self) -> str | None:
        """Current Merkle root hash."""
        return self._tree.get_merkle_root()

    @property
    def length(self) -> int:
        """Number of records in the chain."""
        return len(self._tree.leaves)
