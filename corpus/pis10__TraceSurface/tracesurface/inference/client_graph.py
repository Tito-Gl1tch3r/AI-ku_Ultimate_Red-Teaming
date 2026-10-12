from __future__ import annotations

from collections.abc import Iterable

from tracesurface.models import ClientAliasFact, ClientRef

ClientKey = tuple[str, int, int]


class ClientGraph:
    def __init__(self) -> None:
        self._parent: dict[ClientKey, ClientKey] = {}

    def union(self, a: ClientKey, b: ClientKey) -> None:
        ra, rb = self._root(a), self._root(b)

        if ra != rb:
            self._parent[rb] = ra

    def canonical(self, ref: ClientRef | None) -> ClientKey | None:
        if ref is None:
            return None

        if (
            ref.decl_node_id == 0
            and ref.scope_id == 0
            and not ref.module_id.startswith("<mod:")
        ):
            return None
        return self._root(ref.key())

    @classmethod
    def build(cls, aliases: Iterable[ClientAliasFact]) -> ClientGraph:
        graph = cls()

        for edge in aliases:
            graph.union(edge.left_ref.key(), edge.right_ref.key())
        return graph

    def _root(self, k: ClientKey) -> ClientKey:
        self._parent.setdefault(k, k)

        root = k
        while self._parent[root] != root:
            root = self._parent[root]

        while self._parent[k] != root:
            self._parent[k], k = root, self._parent[k]
        return root
