# -*- coding: utf-8 -*-

# Copyright 2017 Aaron M. Hosford
# See LICENSE.txt for licensing information.


"""
The definitions for the universal object-oriented graph interface.
"""


import collections.abc

from typing import Union, Iterator, Hashable, Any, Optional, MutableMapping, Tuple

from vert.stores.base import GraphStore, EdgeID, Label, VertexID, DirectedEdgeID, UndirectedEdgeID
from vert.stores.memory import MemoryGraphStore
from vert.stores.dbm import DBMGraphStore


__all__ = [
    'Vertex',
    'Edge',
    'Graph',
    'DirectedEdge',
    'UndirectedEdge',
]


VertexOrID = Union[VertexID, 'Vertex']
EdgeOrID = Union[EdgeID, 'Edge', Tuple[VertexOrID, VertexOrID]]


class GraphComponent:
    """
    Base class for graph interface components.
    """

    def __init__(self, graph_store: GraphStore):
        self._graph_store = graph_store

    @staticmethod
    def _to_vid(vertex: VertexOrID, graph_store: Optional[GraphStore]) -> VertexID:
        """
        Convert a vertex or vertex ID to a vertex ID, ensuring that if it's a vertex, it belongs to the correct graph.

        :param vertex: The vertex or vertex ID to be converted.
        :return: The vertex ID.
        """
        if isinstance(vertex, Vertex):
            if graph_store is not None and vertex._graph_store is not graph_store:
                raise ValueError(vertex)
            return vertex.vid
        else:
            return vertex

    @staticmethod
    def _to_eid(edge: EdgeOrID, graph_store: Optional[GraphStore]) -> EdgeID:
        """
        Convert an edge or edge ID to an edge ID, ensuring that if it's an edge, it belongs to the correct graph. Also,
        ensure that the edge ID is expressed as an EdgeID named tuple, not just an ordinary tuple.

        :param edge: The edge or edge ID to be converted.
        :return: The edge ID.
        """
        if isinstance(edge, Edge):
            if graph_store is not None and edge._graph_store is not graph_store:
                raise ValueError(edge)
            return edge.eid
        elif isinstance(edge, EdgeID):
            return edge
        elif isinstance(edge, (tuple, list)):
            assert len(edge) == 2
            return DirectedEdgeID(*(GraphComponent._to_vid(v, graph_store) for v in edge))
        else:
            assert isinstance(edge, (set, frozenset))
            assert 1 <= len(edge) <= 2
            if len(edge) == 1:
                for v in edge:
                    v = GraphComponent._to_vid(v, graph_store)
                    return UndirectedEdgeID(v, v)
            return UndirectedEdgeID(*(GraphComponent._to_vid(v, graph_store) for v in edge))


class FullVertexSet(collections.abc.MutableSet, GraphComponent):
    """
    The complete set of every vertex belonging to the graph.
    """

    def __contains__(self, vertex: VertexOrID) -> bool:
        vid = self._to_vid(vertex, self._graph_store)
        return self._graph_store.has_vertex(vid)

    def __iter__(self) -> Iterator['Vertex']:
        for vid in self._graph_store.iter_vertices():
            yield Vertex(vid, self._graph_store)

    def __len__(self) -> int:
        return self._graph_store.count_vertices()

    def __getitem__(self, vid: VertexID) -> 'Vertex':
        return Vertex(vid, self._graph_store)

    def add(self, vertex: VertexOrID) -> 'Vertex':
        """
        Add a vertex to the graph. If the vertex already belongs to the graph, do nothing. Equivalent to vertex.add().

        :param vertex: The vertex or vertex ID to add to the graph.
        :return: The newly added Vertex instance.
        """
        vid = self._to_vid(vertex, self._graph_store)
        self._graph_store.add_vertex(vid)
        if isinstance(vertex, Vertex):
            return vertex
        else:
            return Vertex(vid, self._graph_store)

    def remove(self, vertex: VertexOrID) -> None:
        """
        Remove a vertex from the graph. If the vertex already does not belong to the graph, raise an exception. All
        incident edges to the vertex are also removed. Equivalent to vertex.remove().

        :param vertex: The vertex or vertex ID to remove from the graph.
        :return: None
        """
        vid = self._to_vid(vertex, self._graph_store)
        if not self._graph_store.discard_vertex(vid):
            raise KeyError(vid)

    def discard(self, vertex: VertexOrID) -> None:
        """
        Remove a vertex from the graph. If the vertex already does not belong to the graph, do nothing. All incident
        edges to the vertex are also removed.Equivalent to vertex.discard().

        :param vertex: The vertex or vertex ID to remove from the graph.
        :return: None
        """
        vid = self._to_vid(vertex, self._graph_store)
        self._graph_store.discard_vertex(vid)


class FullEdgeSet(collections.abc.MutableSet, GraphComponent):
    """
    The complete set of every edge belonging to the graph.
    """

    def __contains__(self, edge: EdgeOrID) -> bool:
        eid = self._to_eid(edge, self._graph_store)
        return self._graph_store.has_edge(eid)

    def __iter__(self) -> Iterator['Edge']:
        for eid in self._graph_store.iter_edges():
            yield Edge.from_eid(eid, self._graph_store)

    def __len__(self) -> int:
        return self._graph_store.count_edges()

    def __getitem__(self, eid: EdgeOrID) -> 'Edge':
        return Edge.from_eid(eid, self._graph_store)

    def add(self, edge: EdgeOrID) -> 'Edge':
        """
        Add an edge to the graph. If the edge already belongs to the graph, do nothing. If either the source or sink
        vertex does not exist, add it. Equivalent to edge.add()

        :param edge: The edge or edge ID to add to the graph.
        :return: The newly added Edge instance.
        """
        eid = self._to_eid(edge, self._graph_store)
        self._graph_store.add_edge(eid)
        return Edge.from_eid(eid, self._graph_store)

    def remove(self, edge: EdgeOrID) -> None:
        """
        Remove an edge from the graph. If the edge already does not belong to the graph, raise an exception. The source
        and sink vertices are not removed. Equivalent to edge.remove().

        :param edge: The edge or edge ID to remove from the graph.
        :return: None
        """
        eid = self._to_eid(edge, self._graph_store)
        if not self._graph_store.discard_edge(eid):
            raise KeyError(eid)

    def discard(self, edge: EdgeOrID) -> None:
        """
        Remove an edge from the graph. If the edge already does not belong to the graph, do nothing. The source and sink
        vertices are not removed. Equivalent to edge.remove().

        :param edge: The edge or edge ID to remove from the graph.
        :return: None
        """
        eid = self._to_eid(edge, self._graph_store)
        self._graph_store.discard_edge(eid)


class UniqueVertexSet(collections.abc.Set, GraphComponent):
    """
    A set containing exactly one vertex.
    """

    def __init__(self, vid, graph_store: GraphStore):
        GraphComponent.__init__(self, graph_store)
        self._vid = vid

    def __contains__(self, vertex: VertexOrID) -> bool:
        vid = self._to_vid(vertex, self._graph_store)
        return vid == self._vid

    def __iter__(self) -> Iterator['Vertex']:
        yield Vertex(self._vid, self._graph_store)

    def __len__(self) -> int:
        return 1


class SourceVertexSet(collections.abc.MutableSet, GraphComponent):
    """
    The set containing every vertex which is the source of an edge that shares the same given sink.
    """

    def __init__(self, vid: VertexID, graph_store: GraphStore):
        GraphComponent.__init__(self, graph_store)
        self._vid = vid

    def __contains__(self, vertex: VertexOrID) -> bool:
        vid = self._to_vid(vertex, self._graph_store)
        eid = DirectedEdgeID(vid, self._vid)
        return self._graph_store.has_edge(eid)

    def __iter__(self) -> Iterator['Vertex']:
        for eid in self._graph_store.iter_inbound(self._vid):
            yield Vertex(eid.source, self._graph_store)

    def __len__(self) -> int:
        return self._graph_store.count_inbound(self._vid)

    def add(self, vertex: VertexOrID) -> 'Vertex':
        """
        Add an edge connecting this vertex as the source to the shared given sink. If the edge already exists, do
        nothing. If either source or sink vertex does not exist, add it to the graph as well.

        :param vertex: The vertex or vertex ID to connect to the shared sink.
        :return: The source Vertex instance.
        """
        vid = self._to_vid(vertex, self._graph_store)
        eid = DirectedEdgeID(vid, self._vid)
        self._graph_store.add_edge(eid)
        return Vertex(vid, self._graph_store)

    def remove(self, vertex: VertexOrID) -> None:
        """
        Remove the edge connecting this vertex as the sink to the shared given sink. The source and sink vertices are
        not removed. If the edge does not exist, raise an exception.

        :param vertex: The source vertex or vertex ID of the edge to be removed.
        :return: None
        """
        vid = self._to_vid(vertex, self._graph_store)
        eid = DirectedEdgeID(vid, self._vid)
        if not self._graph_store.discard_edge(eid):
            raise KeyError(vid)

    def discard(self, vertex: VertexOrID) -> None:
        """
        Remove the edge connecting this vertex as the sink to the shared given sink. The source and sink vertices are
        not removed. If the edge does not exist, do nothing.

        :param vertex: The source vertex or vertex ID of the edge to be removed.
        :return: None
        """
        vid = self._to_vid(vertex, self._graph_store)
        eid = DirectedEdgeID(vid, self._vid)
        self._graph_store.discard_edge(eid)


class InboundEdgeSet(collections.abc.Set, GraphComponent):
    """
    The set of all edges having the given vertex as their shared sink.
    """

    def __init__(self, vid: VertexID, graph_store: GraphStore):
        GraphComponent.__init__(self, graph_store)
        self._vid = vid

    @property
    def sources(self) -> SourceVertexSet:
        """The set of all source vertices for each edge in this edge set."""
        return SourceVertexSet(self._vid, self._graph_store)

    @property
    def sinks(self) -> UniqueVertexSet:
        """The set of all sink vertices for each edge in this edge set."""
        return UniqueVertexSet(self._vid, self._graph_store)

    def __contains__(self, edge: EdgeOrID) -> bool:
        eid = self._to_eid(edge, self._graph_store)
        if not isinstance(eid, DirectedEdgeID):
            return False
        if self._vid != eid.sink:
            return False
        return self._graph_store.has_edge(eid)

    def __iter__(self) -> Iterator['Edge']:
        for eid in self._graph_store.iter_inbound(self._vid):
            yield DirectedEdge(eid, self._graph_store)

    def __len__(self) -> int:
        return self._graph_store.count_inbound(self._vid)

    def __getitem__(self, vertex: VertexOrID) -> 'Edge':
        vid = self._to_vid(vertex, self._graph_store)
        eid = DirectedEdgeID(vid, self._vid)
        return DirectedEdge(eid, self._graph_store)


class SinkVertexSet(collections.abc.MutableSet, GraphComponent):
    """
    The set containing every vertex which is the sink of an edge that shares the same given source.
    """

    def __init__(self, vid: VertexID, graph_store: GraphStore):
        GraphComponent.__init__(self, graph_store)
        self._vid = vid

    def __contains__(self, vertex: VertexOrID) -> bool:
        vid = self._to_vid(vertex, self._graph_store)
        eid = DirectedEdgeID(self._vid, vid)
        return self._graph_store.has_edge(eid)

    def __iter__(self) -> Iterator['Vertex']:
        for eid in self._graph_store.iter_outbound(self._vid):
            yield Vertex(eid.sink, self._graph_store)

    def __len__(self) -> int:
        return self._graph_store.count_outbound(self._vid)

    def add(self, vertex: VertexOrID) -> 'Vertex':
        """
        Add an edge connecting the shared given source to this vertex as the sink. If the edge already exists, do
        nothing. If either source or sink vertex does not exist, add it to the graph as well.

        :param vertex: The vertex or vertex ID to be connected to from the shared source.
        :return: The sink Vertex instance.
        """
        vid = self._to_vid(vertex, self._graph_store)
        eid = DirectedEdgeID(self._vid, vid)
        self._graph_store.add_edge(eid)
        return Vertex(vid, self._graph_store)

    def remove(self, vertex: VertexOrID) -> None:
        """
        Remove the edge connecting the shared given source to this vertex as the sink. The source and sink vertices are
        not removed. If the edge does not exist, raise an exception.

        :param vertex: The sink vertex or vertex ID of the edge to be removed.
        :return: None
        """
        vid = self._to_vid(vertex, self._graph_store)
        eid = DirectedEdgeID(self._vid, vid)
        if not self._graph_store.discard_edge(eid):
            raise KeyError(vid)

    def discard(self, vertex: VertexOrID) -> None:
        """
        Remove the edge connecting the shared given source to this vertex as the sink. The source and sink vertices are
        not removed. If the edge does not exist, do nothing.

        :param vertex: The sink vertex or vertex ID of the edge to be removed.
        :return: None
        """
        vid = self._to_vid(vertex, self._graph_store)
        eid = DirectedEdgeID(self._vid, vid)
        self._graph_store.discard_edge(eid)


class OutboundEdgeSet(collections.abc.Set, GraphComponent):
    """
    The set of all edges having the given vertex as their shared source.
    """

    def __init__(self, vid: VertexID, graph_store: GraphStore):
        GraphComponent.__init__(self, graph_store)
        self._vid = vid

    @property
    def sources(self) -> UniqueVertexSet:
        """The set of all source vertices for each edge in this edge set."""
        return UniqueVertexSet(self._vid, self._graph_store)

    @property
    def sinks(self):
        """The set of all sink vertices for each edge in this edge set."""
        return SinkVertexSet(self._vid, self._graph_store)

    def __contains__(self, edge: EdgeOrID) -> bool:
        eid = self._to_eid(edge, self._graph_store)
        if not isinstance(eid, DirectedEdgeID):
            return False
        if self._vid != eid.source:
            return False
        return self._graph_store.has_edge(eid)

    def __iter__(self) -> Iterator['Edge']:
        for eid in self._graph_store.iter_outbound(self._vid):
            yield DirectedEdge(eid, self._graph_store)

    def __len__(self) -> int:
        return self._graph_store.count_outbound(self._vid)

    def __getitem__(self, vertex: VertexOrID) -> 'Edge':
        vid = self._to_vid(vertex, self._graph_store)
        eid = DirectedEdgeID(self._vid, vid)
        return DirectedEdge(eid, self._graph_store)


class VertexLabelSet(collections.abc.MutableSet, GraphComponent):
    """
    The set of all labels associated with this vertex.
    """

    def __init__(self, vid: VertexID, graph_store: GraphStore):
        GraphComponent.__init__(self, graph_store)
        self._vid = vid

    def __contains__(self, label: Label) -> bool:
        return self._graph_store.has_vertex_label(self._vid, label)

    def __iter__(self) -> Iterator[Label]:
        return self._graph_store.iter_vertex_labels(self._vid)

    def __len__(self) -> int:
        return self._graph_store.count_vertex_labels(self._vid)

    def add(self, label: Label) -> None:
        """
        Add a label to the vertex. If the label is already attached to the vertex, do nothing.

        :param label: The label to be added.
        :return: None
        """
        self._graph_store.add_vertex_label(self._vid, label)

    def remove(self, label: Label) -> None:
        """
        Remove a label from the vertex. If the label is not attached to the vertex, raise an exception.

        :param label: The label to be removed.
        :return: None
        """
        if not self._graph_store.discard_vertex_label(self._vid, label):
            raise KeyError(label)

    def discard(self, label: Label) -> None:
        """
        Remove a label from the vertex. If the label is not attached to the vertex, do nothing.

        :param label: The label to be removed.
        :return: None
        """
        self._graph_store.discard_vertex_label(self._vid, label)


class EdgeLabelSet(collections.abc.MutableSet, GraphComponent):
    """
    The set of all labels associated with this edge.
    """

    def __init__(self, eid: EdgeID, graph_store: GraphStore):
        GraphComponent.__init__(self, graph_store)
        self._eid = eid

    def __contains__(self, label: Label) -> bool:
        return self._graph_store.has_edge_label(self._eid, label)

    def __iter__(self) -> Iterator[Label]:
        return self._graph_store.iter_edge_labels(self._eid)

    def __len__(self) -> int:
        return self._graph_store.count_edge_labels(self._eid)

    def add(self, label: Label) -> None:
        """
        Add a label to the edge. If the label is already attached to the edge, do nothing.

        :param label: The label to be added.
        :return: None
        """
        self._graph_store.add_edge_label(self._eid, label)

    def remove(self, label: Label) -> None:
        """
        Remove a label from the edge. If the label is not attached to the edge, raise an exception.

        :param label: The label to be removed.
        :return: None
        """
        if not self._graph_store.discard_edge_label(self._eid, label):
            raise KeyError(label)

    def discard(self, label: Label) -> None:
        """
        Remove a label from the edge. If the label is not attached to the edge, do nothing.

        :param label: The label to be removed.
        :return: None
        """
        self._graph_store.discard_edge_label(self._eid, label)


class VertexDataMap(collections.abc.MutableMapping, GraphComponent):
    """
    A dictionary mapping out the key/value pairs associated with the vertex.
    """

    def __init__(self, vid: VertexID, graph_store: GraphStore):
        GraphComponent.__init__(self, graph_store)
        self._vid = vid

    def __contains__(self, key: Hashable) -> bool:
        return self._graph_store.has_vertex_data(self._vid, key)

    def __iter__(self) -> Iterator[Hashable]:
        return self._graph_store.iter_vertex_data_keys(self._vid)

    def __len__(self) -> int:
        return self._graph_store.count_vertex_data_keys(self._vid)

    def __getitem__(self, key: Hashable) -> Any:
        if not self._graph_store.has_vertex_data(self._vid, key):
            raise KeyError(key)
        return self._graph_store.get_vertex_data(self._vid, key)

    def __setitem__(self, key: Hashable, value: Any) -> None:
        self._graph_store.set_vertex_data(self._vid, key, value)

    def __delitem__(self, key: Hashable) -> None:
        if not self._graph_store.discard_vertex_data(self._vid, key):
            raise KeyError(key)


class EdgeDataMap(collections.abc.MutableMapping, GraphComponent):
    """
    A dictionary mapping out the key/value pairs associated with the edge.
    """

    def __init__(self, eid: EdgeID, graph_store: GraphStore):
        GraphComponent.__init__(self, graph_store)
        self._eid = eid

    def __contains__(self, key: Hashable) -> bool:
        return self._graph_store.has_edge_data(self._eid, key)

    def __iter__(self) -> Iterator[Hashable]:
        return self._graph_store.iter_edge_data_keys(self._eid)

    def __len__(self) -> int:
        return self._graph_store.count_edge_data_keys(self._eid)

    def __getitem__(self, key: Hashable) -> Any:
        if not self._graph_store.has_edge_data(self._eid, key):
            raise KeyError(key)
        return self._graph_store.get_edge_data(self._eid, key)

    def __setitem__(self, key: Hashable, value: Any) -> None:
        self._graph_store.set_edge_data(self._eid, key, value)

    def __delitem__(self, key: Hashable) -> None:
        if not self._graph_store.discard_edge_data(self._eid, key):
            raise KeyError(key)


class Vertex(GraphComponent):
    """
    A *potential* vertex of the graph. Check the exists property to determine if the vertex belongs to the graph or not.
    """

    def __init__(self, vid: VertexID, graph_store: GraphStore):
        super().__init__(graph_store)
        self._vid = vid

    def __str__(self):
        return repr(self._vid)

    def __repr__(self):
        return '%s(%r, %r)' % (type(self).__name__, self._vid, self._graph_store)

    def __hash__(self):
        return hash(self._vid)

    def __eq__(self, other: 'Vertex'):
        if not isinstance(other, Vertex):
            return NotImplemented
        return self._vid == other._vid and self._graph_store is other._graph_store

    def __ne__(self, other: 'Vertex'):
        if not isinstance(other, Vertex):
            return NotImplemented
        return self._vid != other._vid or self._graph_store is not other._graph_store

    def __bool__(self) -> bool:
        return self._graph_store.has_vertex(self._vid)

    @property
    def vid(self) -> VertexID:
        """
        The vertex's unique ID.
        """
        return self._vid

    @property
    def labels(self) -> VertexLabelSet:
        """
        The set of labels associated with the vertex.
        """
        return VertexLabelSet(self._vid, self._graph_store)

    @property
    def data(self) -> VertexDataMap:
        """
        The key/value pairs associated with the vertex.
        """
        return VertexDataMap(self._vid, self._graph_store)

    @property
    def exists(self) -> bool:
        """
        Whether or not the vertex exists in the graph.
        """
        return self._graph_store.has_vertex(self._vid)

    @property
    def inbound(self) -> InboundEdgeSet:
        """The set of edges that have this vertex as their sink."""
        return InboundEdgeSet(self._vid, self._graph_store)

    @property
    def outbound(self) -> OutboundEdgeSet:
        """The set of edges that have this vertex as their source."""
        return OutboundEdgeSet(self._vid, self._graph_store)

    @property
    def sources(self):
        """The set of vertices that are sources for edges that have this vertex as their sink."""
        return SourceVertexSet(self._vid, self._graph_store)

    @property
    def sinks(self):
        """The set of vertices that are sinks for edges that have this vertex as their source."""
        return SinkVertexSet(self._vid, self._graph_store)

    def add(self) -> 'Vertex':
        """
        Add the vertex to the graph. If the vertex already exists, do nothing.

        :return: The Vertex instance.
        """
        self._graph_store.add_vertex(self._vid)
        return self

    def remove(self) -> None:
        """
        Remove the vertex from the graph. If the vertex was not in the graph, raise an exception. Any incident edges to
        the vertex are also removed.

        :return: None
        """
        if not self._graph_store.discard_vertex(self._vid):
            raise KeyError(self._vid)

    def discard(self) -> None:
        """
        Remove the vertex from the graph. If the vertex was not in the graph, do nothing. Any incident edges to the
        vertex are also removed.

        :return: None
        """
        self._graph_store.discard_vertex(self._vid)


class Edge(GraphComponent):
    """
    A *potential* edge of the graph. Check the exists property to determine if the edge belongs to the graph or not.
    """

    @classmethod
    def from_eid(cls, eid: EdgeOrID, graph_store: GraphStore) -> 'Edge':
        eid = cls._to_eid(eid, None)
        if isinstance(eid, DirectedEdgeID):
            return DirectedEdge(eid, graph_store)
        else:
            return UndirectedEdge(eid, graph_store)

    def __init__(self, eid: EdgeID, graph_store: GraphStore):
        super().__init__(graph_store)
        if not isinstance(eid, EdgeID):
            eid = self._to_eid(eid, self._graph_store)
        self._eid = eid

    def __str__(self):
        return repr(self._eid)

    def __repr__(self):
        return '%s(%r, %r)' % (type(self).__name__, self._eid, self._graph_store)

    def __hash__(self):
        return hash(self._eid)

    def __eq__(self, other: 'Edge'):
        if not isinstance(other, Edge):
            return NotImplemented
        return self._eid == other._eid and self._graph_store is other._graph_store

    def __ne__(self, other: 'Edge'):
        if not isinstance(other, Edge):
            return NotImplemented
        return self._eid != other._eid or self._graph_store is not other._graph_store

    def __bool__(self) -> bool:
        return self._graph_store.has_edge(self._eid)

    @property
    def is_directed(self) -> bool:
        raise NotImplementedError()

    @property
    def eid(self) -> EdgeID:
        """The edge's unique ID."""
        return self._eid

    @property
    def vertices(self) -> Tuple[Vertex, Vertex]:
        """A tuple of the vertices that the edge connects."""
        # noinspection PyTypeChecker
        return tuple(Vertex(vid, self._graph_store) for vid in self._eid.vertices)

    @property
    def labels(self) -> EdgeLabelSet:
        """The labels associated with the edge."""
        # noinspection PyTypeChecker
        return EdgeLabelSet(self._eid, self._graph_store)

    @property
    def data(self) -> EdgeDataMap:
        """The key/value pairs associated with the edge."""
        # noinspection PyTypeChecker
        return EdgeDataMap(self._eid, self._graph_store)

    @property
    def exists(self) -> bool:
        """Whether or not the edge exists in the graph."""
        return self._graph_store.has_edge(self._eid)

    def add(self) -> 'Edge':
        """
        Add the edge to the graph. If the edge already exists, do nothing. If either source or sink does not exist,
        create it.

        :return: This Edge instance.
        """
        raise NotImplementedError()

    def remove(self) -> None:
        """
        Remove the edge from the graph. If the edge is not in the graph, raise an exception. The source and sink are
        not removed by this operation.

        :return: None
        """
        if not self._graph_store.discard_edge(self._eid):
            raise KeyError(self._eid)

    def discard(self) -> None:
        """
        Remove the edge from the graph. If the edge is not in the graph, do nothing. The source and sink are not
        removed by this operation.

        :return: None
        """
        self._graph_store.discard_edge(self._eid)


class DirectedEdge(Edge):
    """
    A *potential* directed edge of the graph. Check the exists property to determine if the edge belongs to the graph
    or not.
    """

    def __init__(self, eid: EdgeID, graph_store: GraphStore):
        super().__init__(eid, graph_store)
        if not isinstance(self._eid, DirectedEdgeID):
            raise TypeError(eid)

    @property
    def is_directed(self) -> bool:
        return True

    @property
    def source(self) -> Vertex:
        """The vertex that is the source of the edge."""
        assert isinstance(self._eid, DirectedEdgeID)
        return Vertex(self._eid.source, self._graph_store)

    @property
    def sink(self) -> Vertex:
        """The vertex that is the sink of the edge."""
        assert isinstance(self._eid, DirectedEdgeID)
        return Vertex(self._eid.sink, self._graph_store)

    @property
    def undirected(self) -> 'UndirectedEdge':
        """The undirected edge connecting the two vertices."""
        return UndirectedEdge(UndirectedEdgeID(*self._eid), self._graph_store)

    def add(self) -> 'DirectedEdge':
        """
        Add the edge to the graph. If the edge already exists, do nothing. If either source or sink does not exist,
        create it.

        :return: This Edge instance.
        """
        self._graph_store.add_edge(self._eid)
        return self


class UndirectedEdge(Edge):
    """
    A *potential* undirected edge of the graph. Check the exists property to determine if the edge belongs to the graph
    or not.
    """

    def __init__(self, eid: EdgeID, graph_store: GraphStore):
        super().__init__(eid, graph_store)
        if not isinstance(self._eid, UndirectedEdgeID):
            raise TypeError(self._eid)

    @property
    def is_directed(self) -> bool:
        return False

    def add(self) -> 'UndirectedEdge':
        """
        Add the edge to the graph. If the edge already exists, do nothing. If either source or sink does not exist,
        create it.

        :return: This Edge instance.
        """
        self._graph_store.add_edge(self._eid)
        return self


class Graph:
    """
    A graph, consisting of a set of vertices and edges, such that every edge's source and sink belong to the set of
    vertices.
    """

    def __init__(self, store: Optional[Union[GraphStore, str, MutableMapping[bytes, bytes]]]=None):
        if store is None:
            store = MemoryGraphStore()
        elif not isinstance(store, GraphStore):
            store = DBMGraphStore(store)
        assert isinstance(store, GraphStore)
        self._graph_store = store

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    @property
    def is_open(self):
        """Whether or not the graph is open. Once a graph is closed, it cannot be operated on."""
        return self._graph_store.is_open

    def close(self):
        """Close the graph."""
        self._graph_store.close()

    @property
    def vertices(self) -> FullVertexSet:
        """The set of all vertices in the graph."""
        return FullVertexSet(self._graph_store)

    @property
    def edges(self) -> FullEdgeSet:
        """The set of all edges in the graph."""
        return FullEdgeSet(self._graph_store)
