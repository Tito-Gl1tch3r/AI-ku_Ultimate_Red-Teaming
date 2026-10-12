# -*- coding: utf-8 -*-

# Copyright 2017 Aaron M. Hosford
# See LICENSE.txt for licensing information.


"""
Definitions for GraphStore abstract base class and type descriptors for labels and vertex/edge IDs.
"""


from typing import NewType, Hashable, Any, Optional, Iterator, NamedTuple, Union


__all__ = [
    'GraphStore',
    'VertexID',
    'EdgeID',
    'DirectedEdgeID',
    'UndirectedEdgeID',
    'Label',
]


VertexID = NewType('VertexID', Union[int, str, bytes])
Label = NewType('Label', Hashable)


class EdgeID:
    """
    Common base class for DirectedEdgeID and UndirectedEdgeID.
    """

    @property
    def vertices(self) -> Iterator[VertexID]:
        """An iterator, guaranteed to yield exactly 2 vertices, in the same order every time."""
        raise NotImplementedError()

    @property
    def is_directed(self) -> bool:
        """Whether or not the edge is directed."""
        raise NotImplementedError()

    def __iter__(self) -> Iterator[VertexID]:
        raise NotImplementedError()


_DirectedEdgeID = NamedTuple('DirectedEdgeId', [('source', VertexID), ('sink', VertexID)])


class DirectedEdgeID(_DirectedEdgeID, EdgeID):
    """
    Edge ID signifiers for directed edges.
    """

    def __new__(cls, source: VertexID, sink: VertexID, *args, **kwargs):
        return _DirectedEdgeID.__new__(cls, source, sink, *args, **kwargs)

    @property
    def vertices(self) -> Iterator[VertexID]:
        """An iterator, guaranteed to yield exactly 2 vertices, in the same order every time."""
        yield from self

    @property
    def is_directed(self) -> bool:
        """Whether or not the edge is directed."""
        return True

    def __iter__(self) -> Iterator[VertexID]:
        return super().__iter__()


class UndirectedEdgeID(frozenset, EdgeID):
    """
    Edge ID signifiers for undirected edges.
    """

    def __init__(self, vid1: VertexID, vid2: VertexID):
        super().__init__((vid1, vid2))

    def __new__(cls, vid1: VertexID, vid2: VertexID, *args, **kwargs):
        return frozenset.__new__(cls, (vid1, vid2), *args, **kwargs)

    @property
    def is_directed(self) -> bool:
        """Whether or not the edge is directed."""
        return False

    @property
    def vertices(self) -> Iterator[VertexID]:
        """An iterator, guaranteed to yield exactly 2 vertices, in the same order every time."""
        if len(self) == 1:
            for v in self:
                yield v
                yield v
        else:
            try:
                yield from sorted(self)
            except TypeError:
                yield from sorted(self, key=repr)


class GraphStore:
    """
    The abstract interface for graph stores. All graph stores must support this interface in order to be accessed via
    the first-class object interface (the Graph, Vertex, and Edge classes).
    """

    @property
    def is_open(self) -> bool:
        """A Boolean value indicating whether the graph store is open. When a graph store is closed, it cannot be
        accessed."""
        return True  # By default, always open

    def close(self) -> None:
        """Perform a proper shutdown of the graph store, ensuring that if the graph store is persistent, it will be
        in a consistent on-disk state."""
        pass  # By default, a no-op

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def count_vertices(self) -> int:
        """Return the total number of vertices in the graph."""
        raise NotImplementedError()

    def count_edges(self) -> int:
        """Return the total number of edges in the graph."""
        raise NotImplementedError()

    def iter_vertices(self) -> Iterator[VertexID]:
        """Return an iterator over the IDs of every vertex in the graph."""
        raise NotImplementedError()

    def iter_edges(self) -> Iterator[EdgeID]:
        """Return an iterator over the IDs of every edge in the graph."""
        raise NotImplementedError()

    def has_inbound(self, sink: VertexID) -> bool:
        """Return a Boolean value indicating whether the given vertex has at least one inbound edge."""
        raise NotImplementedError()

    def has_outbound(self, source: VertexID) -> bool:
        """Return a Boolean value indicating whether the given vertex has at least one outbound edge."""
        raise NotImplementedError()

    def has_undirected(self, vid: VertexID) -> bool:
        """Return a Boolean value indicating whether the given vertex has at least one undirected edge."""
        raise NotImplementedError()

    def iter_inbound(self, sink: VertexID) -> Iterator[DirectedEdgeID]:
        """Return an iterator over the IDs of every inbound directed edge to this vertex."""
        raise NotImplementedError()

    def iter_outbound(self, source: VertexID) -> Iterator[DirectedEdgeID]:
        """Return an iterator over the IDs of every outbound directed edge from this vertex."""
        raise NotImplementedError()

    def iter_undirected(self, vid: VertexID) -> Iterator[UndirectedEdgeID]:
        """Return an iterator over the IDs of every undirected edge connected to this vertex."""
        raise NotImplementedError()

    def count_inbound(self, sink: VertexID) -> int:
        """Return the number of inbound directed edges to this vertex."""
        raise NotImplementedError()

    def count_outbound(self, source: VertexID) -> int:
        """Return the number of outbound directed edges from this vertex."""
        raise NotImplementedError()

    def count_undirected(self, vid: VertexID) -> int:
        """Return the number of undirected edges connected to this vertex."""
        raise NotImplementedError()

    def has_vertex(self, vid: VertexID) -> bool:
        """Return whether the given ID has a vertex associated with it in the graph."""
        raise NotImplementedError()

    def has_edge(self, eid: EdgeID) -> bool:
        """Return whether the given ID has an edge associated with it in the graph."""
        raise NotImplementedError()

    def add_vertex(self, vid: VertexID) -> None:
        """
        Add a vertex to the graph associated with this ID. If a vertex with the given ID already exists, do nothing.
        """
        raise NotImplementedError()

    def add_edge(self, eid: EdgeID) -> None:
        """
        Add an edge to the graph associated with this ID. If an edge with the given ID already exists, do nothing. If
        either the source or sink vertex of the edge does not exist, add it first.
        """
        raise NotImplementedError()

    def discard_vertex(self, vid: VertexID) -> bool:
        """
        Remove the vertex associated with this ID from the graph. If such a vertex does not exist, do nothing. Any
        incident edges to the vertex are also removed. Return a Boolean indicating whether the vertex was present to
        be removed.
        """
        raise NotImplementedError()

    def discard_edge(self, eid: EdgeID, ignore: Optional[VertexID] = None) -> bool:
        """
        Remove the edge associated with this ID from the graph. If such an edge does not exist, do nothing. The source
        and sink vertex are not removed. Return a Boolean indicating whether the edge was present to be removed.
        """
        raise NotImplementedError()

    def add_vertex_label(self, vid: VertexID, label: Label) -> None:
        """Add a label to the vertex. If the vertex already has the label, do nothing."""
        raise NotImplementedError()

    def has_vertex_label(self, vid: VertexID, label: Label) -> bool:
        """Return a Boolean indicating whether the vertex has the label."""
        raise NotImplementedError()

    def discard_vertex_label(self, vid: VertexID, label: Label) -> bool:
        """
        Remove the label from the vertex. If the vertex does not have the label, do nothing. Return a Boolean indicating
        whether or not a label was removed.
        """
        raise NotImplementedError()

    def iter_vertex_labels(self, vid: VertexID) -> Iterator[Label]:
        """Return an iterator over the labels for the vertex."""
        raise NotImplementedError()

    def count_vertex_labels(self, vid: VertexID) -> int:
        """Return the number of labels the vertex has."""
        raise NotImplementedError()

    def add_edge_label(self, eid: EdgeID, label: Label) -> None:
        """Add a label to the edge. If the edge already has the label, do nothing."""
        raise NotImplementedError()

    def has_edge_label(self, eid: EdgeID, label: Label) -> bool:
        """Return a Boolean indicating whether or not the edge has the label."""
        raise NotImplementedError()

    def discard_edge_label(self, eid: EdgeID, label: Label) -> bool:
        """
        Remove the label from the edge. If the edge does not have the label, do nothing. Return a Boolean indicating
        whether or not a label was removed.
        """
        raise NotImplementedError()

    def iter_edge_labels(self, eid: EdgeID) -> Iterator[Label]:
        """Return an iterator over the labels for the edge."""
        raise NotImplementedError()

    def count_edge_labels(self, eid: EdgeID) -> int:
        """Return the number of labels the edge has."""
        raise NotImplementedError()

    def get_vertex_data(self, vid: VertexID, key: Hashable) -> Any:
        """Return the value stored in the vertex for this key."""
        raise NotImplementedError()

    def set_vertex_data(self, vid: VertexID, key: Hashable, value: Any) -> None:
        """Store a value in the vertex for this key."""
        raise NotImplementedError()

    def has_vertex_data(self, vid: VertexID, key: Hashable) -> bool:
        """Return a Boolean indicating whether a value is stored in the vertex for this key."""
        raise NotImplementedError()

    def discard_vertex_data(self, vid: VertexID, key: Hashable) -> bool:
        """
        Remove the value stored in the vertex under this key. If no value is stored for the key, do nothing. Return
        a Boolean indicating whether a key/value pair was removed from the vertex.
        """
        raise NotImplementedError()

    def iter_vertex_data_keys(self, vid: VertexID) -> Iterator[Hashable]:
        """Return an iterator over the keys for which data is stored in the vertex."""
        raise NotImplementedError()

    def count_vertex_data_keys(self, vid: VertexID) -> int:
        """Return the number of key/value pairs stored in the vertex."""
        raise NotImplementedError()

    def get_edge_data(self, eid: EdgeID, key: Hashable) -> Any:
        """Return the value stored in the edge for this key."""
        raise NotImplementedError()

    def set_edge_data(self, eid: EdgeID, key: Hashable, value: Any) -> None:
        """Store a value in the edge for this key."""
        raise NotImplementedError()

    def has_edge_data(self, eid: EdgeID, key: Hashable) -> bool:
        """Return a Boolean indicating whether a value is stored in the edge for this key."""
        raise NotImplementedError()

    def discard_edge_data(self, eid: EdgeID, key: Hashable) -> bool:
        """
        Remove the value stored in the edge under this key. If no value is stored for the key, do nothing. Return
        a Boolean indicating whether a key/value pair was removed from the edge.
        """
        raise NotImplementedError()

    def iter_edge_data_keys(self, eid: EdgeID) -> Iterator[Hashable]:
        """Return an iterator over the keys for which data is stored in the edge."""
        raise NotImplementedError()

    def count_edge_data_keys(self, eid: EdgeID) -> int:
        """Return the number of key/value pairs stored in the edge."""
        raise NotImplementedError()
