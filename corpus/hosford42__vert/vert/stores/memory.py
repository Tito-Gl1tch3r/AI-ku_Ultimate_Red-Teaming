# -*- coding: utf-8 -*-

# Copyright 2017 Aaron M. Hosford
# See LICENSE.txt for licensing information.


"""
A non-persistent graph store implemented using standard Python data types.
"""


from typing import Hashable, Any, Optional, Iterator


import vert.stores.base as base


__all__ = [
    'MemoryGraphStore',
]


class MemoryGraphStore(base.GraphStore):
    """
    A Python-only, non-persistent graph store designed for sparse graphs.
    """

    def __init__(self):
        self._forward = {}
        self._backward = {}
        self._dual = {}
        self._vertex_labels = {}
        self._edge_labels = {}
        self._vertex_data = {}
        self._edge_data = {}
        self._edge_count = 0

    def count_vertices(self) -> int:
        """Return the total number of vertices in the graph."""
        return len(self._forward)

    def count_edges(self) -> int:
        """Return the total number of edges in the graph."""
        return self._edge_count

    def iter_vertices(self) -> Iterator[base.VertexID]:
        """Return an iterator over the IDs of every vertex in the graph."""
        return iter(self._forward)

    def iter_edges(self) -> Iterator[base.EdgeID]:
        """Return an iterator over the IDs of every edge in the graph."""
        for source, sinks in self._forward.items():
            for sink in sinks:
                yield base.DirectedEdgeID(source, sink)

        # We have to guarantee that each edge is only yielded once, which is a bit more complicated when edges
        # are undirected. We do that by imposing an artificial order on the IDs (since IDs are not required to be
        # ordered). I know repr is slow, but it's better than building a set to avoid duplicates.
        for left, rights in self._dual.items():
            if left in rights:
                yield base.UndirectedEdgeID(left, left)
            left_repr = repr(left)
            for right in rights:
                if left != right and left_repr < repr(right):
                    yield base.UndirectedEdgeID(left, right)

    def has_inbound(self, sink: base.VertexID) -> bool:
        """Return a Boolean value indicating whether the given vertex has at least one inbound edge."""
        return bool(self._backward.get(sink, ()))

    def has_outbound(self, source: base.VertexID) -> bool:
        """Return a Boolean value indicating whether the given vertex has at least one outbound edge."""
        return bool(self._forward.get(source, ()))

    def has_undirected(self, vid: base.VertexID) -> bool:
        """Return a Boolean value indicating whether the given vertex has at least one undirected edge."""
        return bool(self._dual.get(vid, ()))

    def iter_inbound(self, sink: base.VertexID) -> Iterator[base.DirectedEdgeID]:
        """Return an iterator over the IDs of every inbound directed edge to this vertex."""
        for source in self._backward.get(sink, ()):
            yield base.DirectedEdgeID(source, sink)

    def iter_outbound(self, source: base.VertexID) -> Iterator[base.DirectedEdgeID]:
        """Return an iterator over the IDs of every outbound directed edge from this vertex."""
        for sink in self._backward.get(source, ()):
            yield base.DirectedEdgeID(source, sink)

    def iter_undirected(self, vid: base.VertexID) -> Iterator[base.UndirectedEdgeID]:
        """Return an iterator over the IDs of every undirected edge connected to this vertex."""
        for other in self._dual.get(vid, ()):
            yield base.UndirectedEdgeID(vid, other)

    def count_inbound(self, sink: base.VertexID) -> int:
        """Return the number of inbound directed edges to this vertex."""
        return len(self._backward.get(sink, ()))

    def count_outbound(self, source: base.VertexID) -> int:
        """Return the number of outbound directed edges from this vertex."""
        return len(self._forward.get(source, ()))

    def count_undirected(self, vid: base.VertexID) -> int:
        """Return the number of undirected edges connected to this vertex."""
        return len(self._dual.get(vid, ()))

    def has_vertex(self, vid: base.VertexID) -> bool:
        """Return whether the given ID has a vertex associated with it in the graph."""
        return vid in self._forward

    def has_edge(self, eid: base.EdgeID) -> bool:
        """Return whether the given ID has an edge associated with it in the graph."""
        if isinstance(eid, base.DirectedEdgeID):
            return eid.sink in self._forward.get(eid.source, ())
        else:
            assert isinstance(eid, base.UndirectedEdgeID)
            v1, v2 = eid.vertices
            return v2 in self._dual.get(v1, ())

    def add_vertex(self, vid: base.VertexID) -> None:
        """
        Add a vertex to the graph associated with this ID. If a vertex with the given ID already exists, do nothing.
        """
        if vid not in self._forward:
            self._forward[vid] = set()
            self._backward[vid] = set()
            self._dual[vid] = set()

    def add_edge(self, eid: base.EdgeID) -> None:
        """
        Add an edge to the graph associated with this ID. If an edge with the given ID already exists, do nothing. If
        either the source or sink vertex of the edge does not exist, add it first.
        """
        if isinstance(eid, base.DirectedEdgeID):
            if eid.sink in self._forward.get(eid.source, ()):
                return
            self.add_vertex(eid.source)
            self.add_vertex(eid.sink)
            self._forward[eid.source].add(eid.sink)
            self._backward[eid.sink].add(eid.source)
            self._edge_count += 1
        else:
            assert isinstance(eid, base.UndirectedEdgeID)
            v1, v2 = eid.vertices
            if v2 in self._dual.get(v1, ()):
                return
            self.add_vertex(v1)
            self.add_vertex(v2)
            self._dual[v1].add(v2)
            self._dual[v2].add(v1)

    def discard_vertex(self, vid: base.VertexID) -> bool:
        """
        Remove the vertex associated with this ID from the graph. If such a vertex does not exist, do nothing. Any
        incident edges to the vertex are also removed. Return a Boolean indicating whether the vertex was present to
        be removed.
        """
        if vid not in self._forward:
            return False

        # Remove labels and data
        if vid in self._vertex_labels:
            del self._vertex_labels[vid]
        if vid in self._vertex_data:
            del self._vertex_data[vid]

        # Remove all incident edges.
        for sink in self._forward[vid]:
            self.discard_edge(base.DirectedEdgeID(vid, sink), ignore=vid)
        for source in self._backward[vid]:
            self.discard_edge(base.DirectedEdgeID(source, vid), ignore=vid)
        for other in self._dual[vid]:
            self.discard_edge(base.UndirectedEdgeID(vid, other), ignore=vid)

        # Remove the vertex itself
        del self._forward[vid]
        del self._backward[vid]
        del self._dual[vid]

        return True

    def discard_edge(self, eid: base.EdgeID, ignore: Optional[base.VertexID] = None) -> bool:
        """
        Remove the edge associated with this ID from the graph. If such an edge does not exist, do nothing. The source
        and sink vertex are not removed. Return a Boolean indicating whether the edge was present to be removed.
        """
        if not self.has_edge(eid):
            return False

        # Remove labels and data.
        if eid in self._edge_labels:
            del self._edge_labels[eid]
        if eid in self._edge_data:
            del self._edge_data[eid]

        # Remove the edge itself
        if isinstance(eid, base.DirectedEdgeID):
            if eid.source != ignore:
                self._forward[eid.source].discard(eid.sink)
            if eid.sink != ignore:
                self._backward[eid.sink].discard(eid.source)
        else:
            assert isinstance(eid, base.UndirectedEdgeID)
            v1, v2 = eid.vertices
            if v1 != ignore:
                self._dual[v1].discard(v2)
            if v1 != v2 and v2 != ignore:
                self._dual[v2].discard(v1)

        # Decrement the counter
        self._edge_count -= 1

        return True

    def add_vertex_label(self, vid: base.VertexID, label: base.Label) -> None:
        """Add a label to the vertex. If the vertex already has the label, do nothing."""
        self.add_vertex(vid)
        if vid in self._vertex_labels:
            self._vertex_labels[vid].add(label)
        else:
            self._vertex_labels[vid] = {label}

    def has_vertex_label(self, vid: base.VertexID, label: base.Label) -> bool:
        """Return a Boolean indicating whether the vertex has the label."""
        return label in self._vertex_labels.get(vid, ())

    def discard_vertex_label(self, vid: base.VertexID, label: base.Label) -> bool:
        """
        Remove the label from the vertex. If the vertex does not have the label, do nothing. Return a Boolean indicating
        whether or not a label was removed.
        """
        labels = self._vertex_labels.get(vid, None)
        if labels is None:
            return False
        if label in labels:
            labels.discard(label)
            if not labels:
                del self._vertex_labels[vid]
            return True
        return False

    def iter_vertex_labels(self, vid: base.VertexID) -> Iterator[base.Label]:
        """Return an iterator over the labels for the vertex."""
        return iter(self._vertex_labels.get(vid, ()))

    def count_vertex_labels(self, vid: base.VertexID) -> int:
        """Return the number of labels the vertex has."""
        return len(self._vertex_labels.get(vid, ()))

    def add_edge_label(self, eid: base.EdgeID, label: base.Label) -> None:
        """Add a label to the edge. If the edge already has the label, do nothing."""
        self.add_edge(eid)
        if eid in self._edge_labels:
            self._edge_labels[eid].add(label)
        else:
            self._edge_labels[eid] = {label}

    def has_edge_label(self, eid: base.EdgeID, label: base.Label) -> bool:
        """Return a Boolean indicating whether or not the edge has the label."""
        return label in self._edge_labels.get(eid, ())

    def discard_edge_label(self, eid: base.EdgeID, label: base.Label) -> bool:
        """
        Remove the label from the edge. If the edge does not have the label, do nothing. Return a Boolean indicating
        whether or not a label was removed.
        """
        labels = self._edge_labels.get(eid, None)
        if labels is None:
            return False
        if label in labels:
            labels.discard(label)
            if not labels:
                del self._edge_labels[eid]
            return True
        return False

    def iter_edge_labels(self, eid: base.EdgeID) -> Iterator[base.Label]:
        """Return an iterator over the labels for the edge."""
        return iter(self._edge_labels.get(eid, ()))

    def count_edge_labels(self, eid: base.EdgeID) -> int:
        """Return the number of labels the edge has."""
        return len(self._edge_labels.get(eid, ()))

    def get_vertex_data(self, vid: base.VertexID, key: Hashable) -> Any:
        """Return the value stored in the vertex for this key."""
        if vid in self._vertex_data:
            return self._vertex_data[vid].get(key, None)
        return None

    def set_vertex_data(self, vid: base.VertexID, key: Hashable, value: Any) -> None:
        """Store a value in the vertex for this key."""
        self.add_vertex(vid)
        if vid in self._vertex_data:
            data = self._vertex_data[vid]
        else:
            data = {}
            self._vertex_data[vid] = data
        data[key] = value

    def has_vertex_data(self, vid: base.VertexID, key: Hashable) -> bool:
        """Return a Boolean indicating whether a value is stored in the vertex for this key."""
        return key in self._vertex_data.get(vid, ())

    def discard_vertex_data(self, vid: base.VertexID, key: Hashable) -> bool:
        """
        Remove the value stored in the vertex under this key. If no value is stored for the key, do nothing. Return
        a Boolean indicating whether a key/value pair was removed from the vertex.
        """
        data = self._vertex_data.get(vid, None)
        if data is None:
            return False
        if key in data:
            del data[key]
            if not data:
                del self._vertex_data[vid]
            return True
        return False

    def iter_vertex_data_keys(self, vid: base.VertexID) -> Iterator[Hashable]:
        """Return an iterator over the keys for which data is stored in the vertex."""
        return iter(self._vertex_data.get(vid, ()))

    def count_vertex_data_keys(self, vid: base.VertexID) -> int:
        """Return the number of key/value pairs stored in the vertex."""
        return len(self._vertex_data.get(vid, ()))

    def get_edge_data(self, eid: base.EdgeID, key: Hashable) -> Any:
        """Return the value stored in the edge for this key."""
        if eid in self._edge_data:
            return self._edge_data[eid].get(key, None)
        return None

    def set_edge_data(self, eid: base.EdgeID, key: Hashable, value: Any) -> None:
        """Store a value in the edge for this key."""
        self.add_edge(eid)
        if eid in self._edge_data:
            data = self._edge_data[eid]
        else:
            data = {}
            self._edge_data[eid] = data
        data[key] = value

    def has_edge_data(self, eid: base.EdgeID, key: Hashable) -> bool:
        """Return a Boolean indicating whether a value is stored in the edge for this key."""
        return key in self._edge_data.get(eid, ())

    def discard_edge_data(self, eid: base.EdgeID, key: Hashable) -> bool:
        """
        Remove the value stored in the edge under this key. If no value is stored for the key, do nothing. Return
        a Boolean indicating whether a key/value pair was removed from the edge.
        """
        data = self._edge_data.get(eid, None)
        if data is None:
            return False
        if key in data:
            del data[key]
            if not data:
                del self._edge_data[eid]
            return True
        return False

    def iter_edge_data_keys(self, eid: base.EdgeID) -> Iterator[Hashable]:
        """Return an iterator over the keys for which data is stored in the edge."""
        return iter(self._edge_data.get(eid, ()))

    def count_edge_data_keys(self, eid: base.EdgeID) -> int:
        """Return the number of key/value pairs stored in the edge."""
        return len(self._edge_data.get(eid, ()))
