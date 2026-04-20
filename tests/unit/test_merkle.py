"""Tests for the pure-Python Merkle tree."""

from trustpipe.provenance.merkle import MerkleTree


def test_empty_tree_has_no_root():
    tree = MerkleTree()
    assert tree.get_merkle_root() is None


def test_single_leaf():
    tree = MerkleTree()
    tree.add_leaf("hello", do_hash=True)  # hash it so root is SHA-256
    tree.make_tree()
    root = tree.get_merkle_root()
    assert root is not None
    assert len(root) == 64  # SHA-256 hex


def test_two_leaves_produce_root():
    tree = MerkleTree()
    tree.add_leaf("a", do_hash=False)
    tree.add_leaf("b", do_hash=False)
    tree.make_tree()
    root = tree.get_merkle_root()
    assert root is not None


def test_proof_validates_for_leaf():
    tree = MerkleTree()
    tree.add_leaf("a", do_hash=False)
    tree.add_leaf("b", do_hash=False)
    tree.add_leaf("c", do_hash=False)
    tree.add_leaf("d", do_hash=False)
    tree.make_tree()

    root = tree.get_merkle_root()
    for i in range(4):
        leaf = ["a", "b", "c", "d"][i]
        proof = tree.get_proof(i)
        assert tree.validate_proof(proof, leaf, root), f"Leaf {i} failed validation"


def test_tampered_leaf_fails_validation():
    tree = MerkleTree()
    tree.add_leaf("a", do_hash=False)
    tree.add_leaf("b", do_hash=False)
    tree.make_tree()

    root = tree.get_merkle_root()
    proof = tree.get_proof(0)
    # Tamper: validate "a" proof with "x" value
    assert not tree.validate_proof(proof, "x", root)


def test_different_data_different_roots():
    tree1 = MerkleTree()
    tree1.add_leaf("a", do_hash=False)
    tree1.add_leaf("b", do_hash=False)
    tree1.make_tree()

    tree2 = MerkleTree()
    tree2.add_leaf("a", do_hash=False)
    tree2.add_leaf("c", do_hash=False)
    tree2.make_tree()

    assert tree1.get_merkle_root() != tree2.get_merkle_root()


def test_root_changes_on_append():
    tree = MerkleTree()
    tree.add_leaf("a", do_hash=False)
    tree.make_tree()
    root1 = tree.get_merkle_root()

    tree.add_leaf("b", do_hash=False)
    tree.make_tree()
    root2 = tree.get_merkle_root()

    assert root1 != root2


def test_do_hash_flag():
    tree = MerkleTree()
    tree.add_leaf("hello world", do_hash=True)
    tree.make_tree()
    root = tree.get_merkle_root()
    assert root is not None
