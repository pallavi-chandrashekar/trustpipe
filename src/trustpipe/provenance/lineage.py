"""LineageGraph — DAG traversal for data lineage queries."""

from __future__ import annotations

from dataclasses import dataclass, field

from trustpipe.provenance.record import ProvenanceRecord
from trustpipe.storage.base import StorageBackend


@dataclass
class LineageNode:
    """A node in the lineage DAG."""

    record: ProvenanceRecord
    parents: list[LineageNode] = field(default_factory=list)
    children: list[LineageNode] = field(default_factory=list)
    depth: int = 0


class LineageGraph:
    """DAG of data lineage relationships."""

    def __init__(self, root: LineageNode, nodes: dict[str, LineageNode]) -> None:
        self.root = root
        self.nodes = nodes

    @classmethod
    def build(
        cls,
        record_id: str,
        storage: StorageBackend,
        max_depth: int = 0,
    ) -> LineageGraph | None:
        """Build a lineage graph starting from a record, walking ancestors."""
        record = storage.load_provenance_record(record_id)
        if not record:
            return None

        nodes: dict[str, LineageNode] = {}
        root_node = LineageNode(record=record, depth=0)
        nodes[record.id] = root_node

        queue: list[tuple[LineageNode, int]] = [(root_node, 0)]
        while queue:
            node, depth = queue.pop(0)
            if max_depth and depth >= max_depth:
                continue

            for parent_id in node.record.parent_ids:
                if parent_id in nodes:
                    parent_node = nodes[parent_id]
                else:
                    parent_record = storage.load_provenance_record(parent_id)
                    if not parent_record:
                        continue
                    parent_node = LineageNode(record=parent_record, depth=depth + 1)
                    nodes[parent_id] = parent_node
                    queue.append((parent_node, depth + 1))

                node.parents.append(parent_node)
                parent_node.children.append(node)

        return cls(root=root_node, nodes=nodes)

    def to_tree_string(self) -> str:
        """Render as a text tree for CLI display."""
        lines: list[str] = []
        self._render_node(self.root, lines, prefix="", is_last=True, is_root=True)
        return "\n".join(lines)

    def _render_node(
        self,
        node: LineageNode,
        lines: list[str],
        prefix: str,
        is_last: bool,
        is_root: bool,
    ) -> None:
        connector = "" if is_root else ("└── " if is_last else "├── ")
        verified = "✓" if node.record.merkle_root else "?"
        source = f" ← {node.record.source}" if node.record.source else ""
        rows = f" ({node.record.row_count} rows)" if node.record.row_count else ""

        lines.append(f"{prefix}{connector}[{verified}] {node.record.name}{source}{rows}")

        child_prefix = prefix + ("    " if is_last or is_root else "│   ")
        for i, parent in enumerate(node.parents):
            self._render_node(
                parent, lines, child_prefix, is_last=(i == len(node.parents) - 1), is_root=False
            )
