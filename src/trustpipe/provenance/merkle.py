"""Merkle tree for provenance chain integrity.

Uses pymerkletools if available, falls back to a minimal pure-Python
implementation. This means `pip install trustpipe` has full provenance
verification with zero optional dependencies.
"""

from __future__ import annotations

import hashlib


class MerkleTree:
    """Merkle tree backed by pymerkletools or pure-Python fallback."""

    def __init__(self) -> None:
        self.leaves: list[str] = []
        self._impl: _MerkleImpl = _create_impl()

    def add_leaf(self, value: str, *, do_hash: bool = True) -> None:
        self.leaves.append(value)
        self._impl.add_leaf(value, do_hash=do_hash)

    def make_tree(self) -> None:
        self._impl.make_tree()

    def get_merkle_root(self) -> str | None:
        return self._impl.get_merkle_root()

    def get_proof(self, index: int) -> list[dict[str, str]]:
        return self._impl.get_proof(index)

    def validate_proof(self, proof: list[dict[str, str]], leaf: str, root: str) -> bool:
        return self._impl.validate_proof(proof, leaf, root)

    def reset(self) -> None:
        self.leaves = []
        self._impl = _create_impl()


class _MerkleImpl:
    """Interface for Merkle tree implementations."""

    def add_leaf(self, value: str, *, do_hash: bool = True) -> None: ...
    def make_tree(self) -> None: ...
    def get_merkle_root(self) -> str | None: ...
    def get_proof(self, index: int) -> list[dict[str, str]]: ...
    def validate_proof(self, proof: list[dict[str, str]], leaf: str, root: str) -> bool: ...


def _create_impl() -> _MerkleImpl:
    try:
        import merkletools  # noqa: F401

        return _PyMerkleToolsImpl()
    except ImportError:
        return _PurePythonImpl()


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


class _PyMerkleToolsImpl(_MerkleImpl):
    """Wrapper around pymerkletools."""

    def __init__(self) -> None:
        import merkletools

        self._mt = merkletools.MerkleTools(hash_type="sha256")

    def add_leaf(self, value: str, *, do_hash: bool = True) -> None:
        self._mt.add_leaf(value, do_hash=do_hash)

    def make_tree(self) -> None:
        self._mt.make_tree()

    def get_merkle_root(self) -> str | None:
        root = self._mt.get_merkle_root()
        return root if root else None

    def get_proof(self, index: int) -> list[dict[str, str]]:
        return self._mt.get_proof(index)

    def validate_proof(self, proof: list[dict[str, str]], leaf: str, root: str) -> bool:
        return self._mt.validate_proof(proof, leaf, root)


class _PurePythonImpl(_MerkleImpl):
    """Minimal Merkle tree — no external dependencies."""

    def __init__(self) -> None:
        self._leaves: list[str] = []
        self._tree: list[list[str]] = []

    def add_leaf(self, value: str, *, do_hash: bool = True) -> None:
        self._leaves.append(_sha256(value) if do_hash else value)

    def make_tree(self) -> None:
        if not self._leaves:
            self._tree = []
            return
        level = list(self._leaves)
        self._tree = [level]
        while len(level) > 1:
            next_level = []
            for i in range(0, len(level), 2):
                left = level[i]
                right = level[i + 1] if i + 1 < len(level) else left
                next_level.append(_sha256(left + right))
            level = next_level
            self._tree.append(level)

    def get_merkle_root(self) -> str | None:
        if not self._tree:
            return None
        return self._tree[-1][0] if self._tree[-1] else None

    def get_proof(self, index: int) -> list[dict[str, str]]:
        if not self._tree or index >= len(self._leaves):
            return []
        proof: list[dict[str, str]] = []
        idx = index
        for level in self._tree[:-1]:
            if idx % 2 == 0:
                sibling_idx = idx + 1
                if sibling_idx < len(level):
                    proof.append({"right": level[sibling_idx]})
                else:
                    # Odd number of nodes: duplicate self (standard Merkle behavior)
                    proof.append({"right": level[idx]})
            else:
                proof.append({"left": level[idx - 1]})
            idx //= 2
        return proof

    def validate_proof(self, proof: list[dict[str, str]], leaf: str, root: str) -> bool:
        current = leaf
        for step in proof:
            if "right" in step:
                current = _sha256(current + step["right"])
            elif "left" in step:
                current = _sha256(step["left"] + current)
        return current == root
