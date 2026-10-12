# -*- coding: utf-8 -*-

# Copyright 2017 Aaron M. Hosford
# See LICENSE.txt for licensing information.

"""
A persistent graph store implemented on top of the built-in Python library, dbm.
"""


import ast
import dbm
import json
import time
from typing import Hashable, Any, Optional, Iterator, Union, MutableMapping, NewType


import vert.stores.base as base


__all__ = [
    'DBMGraphStore',
]


VertexData = NewType('VertexData', list)
EdgeData = NewType('EdgeData', list)

COUNT_PREFIX = b'c'
VID_PREFIX = b'v'
EID_PREFIX = b'e'

LABEL_INDEX = 0
DATA_INDEX = 1
SOURCES_INDEX = 2
SINKS_INDEX = 3
UNDIRECTED_INDEX = 4


class DBMGraphStore(base.GraphStore):
    """
    A Python-only persistent graph store based on the built-in dbm module, with optional memory-level caching for
    performance gains at the expense of robustness to incorrect shutdowns.
    """

    def __init__(self, path: Union[str, MutableMapping[bytes, bytes]], v_cache_size: int = 100,
                 e_cache_size: int = 100):
        self._db = None  # So it's defined in __del__ in case we get an error opening the database
        self._auto_close_db = False
        self._is_open = True

        self._v_cache_size = v_cache_size
        self._v_cache = {}
        self._v_cache_times = {}
        self._v_cache_dirty = set()

        self._e_cache_size = e_cache_size
        self._e_cache = {}
        self._e_cache_times = {}
        self._e_cache_dirty = set()

        self._v_count = None
        self._v_count_dirty = False

        self._e_count = None
        self._e_count_dirty = False

        if isinstance(path, str):
            self._auto_close_db = True
            self._db = dbm.open(path, flag='c')
        else:
            self._db = path
            if hasattr(self._db, 'is_open'):
                # noinspection PyUnresolvedReferences
                self._is_open = self._db.is_open

    def __del__(self) -> None:
        self.close()

    @property
    def is_open(self) -> bool:
        """A Boolean value indicating whether the graph store is open. When a graph store is closed, it cannot be
        accessed."""
        return self._is_open

    def close(self):
        """Perform a proper shutdown of the graph store, ensuring that if the graph store is persistent, it will be
        in a consistent on-disk state."""
        if not self._is_open:
            return
        self.flush()
        if self._auto_close_db and hasattr(self._db, 'close'):
            # noinspection PyUnresolvedReferences
            self._db.close()
        self._is_open = False

    @property
    def vertex_cache_size(self) -> int:
        """The number of vertices that are cached in-memory. Set to zero to turn off vertex caching."""
        return self._v_cache_size

    @vertex_cache_size.setter
    def vertex_cache_size(self, value: int) -> None:
        """The number of vertices that are cached in-memory. Set to zero to turn off vertex caching."""
        assert value >= 0
        self._v_cache_size = value
        while len(self._v_cache) > self._v_cache_size:
            self._retire_vertex()

    @property
    def edge_cache_size(self) -> int:
        """The number of edges that are cached in-memory. Set to zero to turn off edge caching."""
        return self._e_cache_size

    @edge_cache_size.setter
    def edge_cache_size(self, value: int) -> None:
        """The number of edges that are cached in-memory. Set to zero to turn off edge caching."""
        assert value >= 0
        self._e_cache_size = value
        while len(self._e_cache) > self._e_cache_size:
            self._retire_vertex()

    @staticmethod
    def _encode_key(key: Any, prefix: bytes) -> bytes:
        """Encode a key to a byte string."""
        if isinstance(key, base.EdgeID) and prefix == EID_PREFIX:
            key = (tuple(key.vertices), isinstance(key, base.DirectedEdgeID))
        try:
            assert ast.literal_eval(repr(key)) == key
        except (ValueError, AssertionError):
            raise ValueError(key, repr(key))
        return prefix + repr(key).encode()

    @staticmethod
    def _decode_key(encoded_key: bytes, prefix: bytes) -> Any:
        """Decode a key from a byte string. This is the inverse of the _encode_key() method."""
        assert encoded_key.startswith(prefix)
        result = ast.literal_eval(encoded_key[len(prefix):].decode())
        if prefix == EID_PREFIX:
            (vid1, vid2), directed = result
            if directed:
                result = base.DirectedEdgeID(vid1, vid2)
            else:
                result = base.UndirectedEdgeID(vid1, vid2)
        return result

    def _immediate_read_data(self, key: Any, prefix: bytes) -> Any:
        """
        Immediately read the value associated with a key from disk; no caching is performed and cached values, if any,
        are ignored.
        """
        assert self._is_open
        return json.loads(self._db[self._encode_key(key, prefix)].decode())

    def _immediate_write_data(self, key: Any, prefix: bytes, data: Any) -> None:
        """
        Immediately write a key/value pair to disk; no caching is performed and cached values, if any, are ignored.
        """
        assert self._is_open
        self._db[self._encode_key(key, prefix)] = json.dumps(data).encode()

    def _immediate_del_data(self, key: Any, prefix: bytes) -> None:
        """
        Immediately remove the value associated with a key from disk; no caching is performed and cached values, if any,
        are ignored.
        """
        assert self._is_open
        del self._db[self._encode_key(key, prefix)]

    def _retire_vertex(self, vid: Optional[base.VertexID] = None) -> None:
        """Retire a vertex from the in-memory cache."""
        if vid is None:
            vid = min(self._v_cache_times, key=self._v_cache_times.get)
        data = self._v_cache.pop(vid)
        if vid in self._v_cache_dirty:
            self._immediate_write_data(vid, VID_PREFIX, data)
            self._v_cache_dirty.remove(vid)
        del self._v_cache_times[vid]

    def _retire_edge(self, eid: Optional[base.EdgeID] = None) -> None:
        """Retire an edge from the in-memory cache."""
        if eid is None:
            eid = min(self._e_cache_times, key=self._e_cache_times.get)
        data = self._e_cache.pop(eid)
        if eid in self._e_cache_dirty:
            self._immediate_write_data(eid, EID_PREFIX, data)
            self._e_cache_dirty.remove(eid)
        del self._e_cache_times[eid]

    def _read_vertex(self, vid: base.VertexID) -> VertexData:
        """Read a vertex from the cache or disk. If caching is enabled, ensure the vertex is cached."""
        assert self._is_open
        if not self._v_cache_size:
            return self._immediate_read_data(vid, VID_PREFIX)

        if vid in self._v_cache:
            self._v_cache_times[vid] = time.time()
            return self._v_cache[vid]

        data = self._immediate_read_data(vid, VID_PREFIX)

        # It's important that this comes *after* we attempt to read the data, since reading it can cause a
        # KeyError, at which point we have a key in the times dictionary that isn't in the cache.
        self._v_cache_times[vid] = time.time()

        self._v_cache[vid] = data
        if len(self._v_cache) > self._v_cache_size:
            self._retire_vertex()

        return data

    def _write_vertex(self, vid: base.VertexID, data: VertexData):
        """Write a vertex to the cache or disk. If caching is enabled, ensure the vertex is cached."""
        assert self._is_open
        if not self._v_cache_size:
            self._immediate_write_data(vid, VID_PREFIX, data)
            return

        self._v_cache_times[vid] = time.time()
        self._v_cache_dirty.add(vid)
        if self._v_cache.get(vid, None) is data:
            assert data is not None
            return  # Nothing to do.
        self._v_cache[vid] = data
        if len(self._v_cache) > self._v_cache_size:
            self._retire_vertex()

    def _del_vertex(self, vid: base.VertexID):
        """Remove a vertex from the cache and disk. This operation is always immediate."""
        assert self._is_open
        # No caching for deletions; it doesn't make sense to, since nothing will be accessing it again.
        if vid in self._v_cache:
            del self._v_cache[vid]
            del self._v_cache_times[vid]
            self._v_cache_dirty.discard(vid)
            try:
                self._immediate_del_data(vid, VID_PREFIX)
            except KeyError:
                pass  # Sometimes it won't have made it to disk yet.
        else:
            self._immediate_del_data(vid, VID_PREFIX)

    def _read_edge(self, eid: base.EdgeID) -> EdgeData:
        """Read an edge from the cache or disk. If caching is enabled, ensure the edge is cached."""
        assert self._is_open
        if not self._e_cache_size:
            return self._immediate_read_data(eid, EID_PREFIX)

        if eid in self._e_cache:
            self._e_cache_times[eid] = time.time()
            return self._e_cache[eid]

        data = self._immediate_read_data(eid, EID_PREFIX)

        # It's important that this comes *after* we attempt to read the data, since reading it can cause a
        # KeyError, at which point we have a key in the times dictionary that isn't in the cache.
        self._e_cache_times[eid] = time.time()

        self._e_cache[eid] = data
        if len(self._e_cache) > self._e_cache_size:
            self._retire_vertex()

        return data

    def _write_edge(self, eid: base.EdgeID, data: EdgeData) -> None:
        """Write an edge to the cache or disk. If caching is enabled, ensure the edge is cached."""
        assert self._is_open
        if not self._e_cache_size:
            self._immediate_write_data(eid, EID_PREFIX, data)
            return

        self._e_cache_times[eid] = time.time()
        self._e_cache_dirty.add(eid)
        if self._e_cache.get(eid, None) is data:
            assert data is not None
            return   # Nothing to do.
        self._e_cache[eid] = data
        if len(self._e_cache) > self._e_cache_size:
            self._retire_edge()

    def _del_edge(self, eid: base.EdgeID) -> None:
        """Remove an edge from the cache and disk. This operation is always immediate."""
        assert self._is_open
        # No caching for deletions; it doesn't make sense to, since nothing will be accessing it again.
        if eid in self._e_cache:
            del self._e_cache[eid]
            del self._e_cache_times[eid]
            self._e_cache_dirty.discard(eid)
            try:
                self._immediate_del_data(eid, EID_PREFIX)
            except KeyError:
                return  # Sometimes it won't have made it to disk yet.
        else:
            self._immediate_del_data(eid, EID_PREFIX)

    def flush(self) -> None:
        """Flush all writes to disk and clear all caches."""
        for vid in sorted(self._v_cache_times, key=self._v_cache_times.get):
            self._retire_vertex(vid)
        for eid in sorted(self._e_cache_times, key=self._e_cache_times.get):
            self._retire_edge(eid)
        if self._v_count_dirty:
            self._immediate_write_data(VID_PREFIX, COUNT_PREFIX, self._v_count)
            self._v_count_dirty = False
        if self._e_count_dirty:
            self._immediate_write_data(EID_PREFIX, COUNT_PREFIX, self._e_count)
            self._e_count_dirty = False
        if hasattr(self._db, 'sync'):
            # noinspection PyUnresolvedReferences
            self._db.sync()

    def count_vertices(self) -> int:
        """Return the total number of vertices in the graph."""
        if self._v_count is None:
            try:
                self._v_count = int(self._immediate_read_data(VID_PREFIX, COUNT_PREFIX))
            except KeyError:
                self._v_count = 0
                self._v_count_dirty = True
        assert isinstance(self._v_count, int)
        return self._v_count

    def count_edges(self) -> int:
        """Return the total number of edges in the graph."""
        if self._e_count is None:
            try:
                self._e_count = int(self._immediate_read_data(EID_PREFIX, COUNT_PREFIX))
            except KeyError:
                self._e_count = 0
                self._e_count_dirty = True
        assert isinstance(self._e_count, int)
        return self._e_count

    def iter_vertices(self) -> Iterator[base.VertexID]:
        """Return an iterator over the IDs of every vertex in the graph."""
        self.flush()
        for key in self._db.keys():
            if key.startswith(VID_PREFIX):
                yield self._decode_key(key, VID_PREFIX)

    def iter_edges(self) -> Iterator[base.EdgeID]:
        """Return an iterator over the IDs of every edge in the graph."""
        self.flush()
        for key in self._db.keys():
            if key.startswith(EID_PREFIX):
                yield self._decode_key(key, EID_PREFIX)

    def has_inbound(self, sink: base.VertexID) -> bool:
        """Return a Boolean value indicating whether the given vertex has at least one inbound edge."""
        try:
            return bool(self._retire_vertex(sink)[SOURCES_INDEX])
        except KeyError:
            return False

    def has_outbound(self, source: base.VertexID) -> bool:
        """Return a Boolean value indicating whether the given vertex has at least one outbound edge."""
        try:
            return bool(self._read_vertex(source)[SINKS_INDEX])
        except KeyError:
            return False

    def has_undirected(self, vid: base.VertexID) -> bool:
        """Return a Boolean value indicating whether the given vertex has at least one undirected edge."""
        try:
            return bool(self._read_vertex(vid)[UNDIRECTED_INDEX])
        except KeyError:
            return False

    def iter_inbound(self, sink: base.VertexID) -> Iterator[base.DirectedEdgeID]:
        """Return an iterator over the IDs of every inbound directed edge to this vertex."""
        try:
            for key in self._read_vertex(sink)[SOURCES_INDEX]:
                yield base.DirectedEdgeID(key, sink)
        except KeyError:
            pass

    def iter_outbound(self, source: base.VertexID) -> Iterator[base.DirectedEdgeID]:
        """Return an iterator over the IDs of every outbound directed edge from this vertex."""
        try:
            for key in self._read_vertex(source)[SINKS_INDEX]:
                yield base.DirectedEdgeID(source, key)
        except KeyError:
            pass

    def iter_undirected(self, vid: base.VertexID) -> Iterator[base.UndirectedEdgeID]:
        """Return an iterator over the IDs of every undirected edge connected to this vertex."""
        try:
            for key in self._read_vertex(vid)[UNDIRECTED_INDEX]:
                yield base.UndirectedEdgeID(vid, key)
        except KeyError:
            pass

    def count_inbound(self, sink: base.VertexID) -> int:
        """Return the number of inbound directed edges to this vertex."""
        try:
            return len(self._read_vertex(sink)[SOURCES_INDEX])
        except KeyError:
            return 0

    def count_outbound(self, source: base.VertexID) -> int:
        """Return the number of outbound directed edges from this vertex."""
        try:
            return len(self._read_vertex(source)[SINKS_INDEX])
        except KeyError:
            return 0

    def count_undirected(self, vid: base.VertexID) -> int:
        """Return the number of undirected edges connected to this vertex."""
        try:
            return len(self._read_vertex(vid)[UNDIRECTED_INDEX])
        except KeyError:
            return 0

    def has_vertex(self, vid: base.VertexID) -> bool:
        """Return whether the given ID has a vertex associated with it in the graph."""
        return vid in self._v_cache or self._encode_key(vid, VID_PREFIX) in self._db

    def has_edge(self, eid: base.EdgeID) -> bool:
        """Return whether the given ID has an edge associated with it in the graph."""
        return eid in self._e_cache or self._encode_key(eid, EID_PREFIX) in self._db

    def add_vertex(self, vid: base.VertexID) -> None:
        """
        Add a vertex to the graph associated with this ID. If a vertex with the given ID already exists, do nothing.
        """
        if not self.has_vertex(vid):
            data = [
                [],  # Labels
                {},  # Data
                [],  # Sources
                [],  # Sinks
                [],  # Undirected
            ]
            self._write_vertex(vid, data)
            self._v_count = self.count_vertices() + 1
            self._v_count_dirty = True

    def add_edge(self, eid: base.EdgeID) -> None:
        """
        Add an edge to the graph associated with this ID. If an edge with the given ID already exists, do nothing. If
        either the source or sink vertex of the edge does not exist, add it first.
        """
        if not self.has_edge(eid):
            for vertex in eid:
                self.add_vertex(vertex)
            data = [
                [],  # Labels,
                {},  # Data
            ]
            self._write_edge(eid, data)

            if isinstance(eid, base.DirectedEdgeID):
                source_data = self._read_vertex(eid.source)
                source_data[SINKS_INDEX].append(eid.sink)
                self._write_vertex(eid.source, source_data)

                sink_data = self._read_vertex(eid.sink)
                sink_data[SOURCES_INDEX].append(eid.source)
                self._write_vertex(eid.sink, sink_data)
            else:
                assert isinstance(eid, base.UndirectedEdgeID)
                v1, v2 = eid.vertices
                v1_data = self._read_vertex(v1)
                v1_data[UNDIRECTED_INDEX].append(v2)
                self._write_vertex(v1, v1_data)

                if v1 != v2:
                    v2_data = self._read_vertex(v2)
                    v2_data[UNDIRECTED_INDEX].append(v1)
                    self._write_vertex(v2, v2_data)

            self._e_count = self.count_edges() + 1
            self._e_count_dirty = True

    def discard_vertex(self, vid: base.VertexID) -> bool:
        """
        Remove the vertex associated with this ID from the graph. If such a vertex does not exist, do nothing. Any
        incident edges to the vertex are also removed. Return a Boolean indicating whether the vertex was present to
        be removed.
        """
        try:
            _, _, sources, sinks, undirected = self._read_vertex(vid)
        except KeyError:
            return False

        for source in sources:
            self.discard_edge(base.DirectedEdgeID(source, vid), ignore=vid)
        for sink in sinks:
            self.discard_edge(base.DirectedEdgeID(vid, sink), ignore=vid)
        for other in undirected:
            self.discard_edge(base.UndirectedEdgeID(vid, other), ignore=vid)

        self._del_vertex(vid)
        self._v_count = self.count_vertices() - 1
        self._v_count_dirty = True

        return True

    def discard_edge(self, eid: base.EdgeID, ignore: Optional[base.VertexID] = None) -> bool:
        """
        Remove the edge associated with this ID from the graph. If such an edge does not exist, do nothing. The source
        and sink vertex are not removed. Return a Boolean indicating whether the edge was present to be removed.
        """
        try:
            self._del_edge(eid)
        except KeyError:
            return False

        if isinstance(eid, base.DirectedEdgeID):
            if eid.source != ignore:
                source_data = self._read_vertex(eid.source)
                source_data[SINKS_INDEX].remove(eid.sink)
                self._write_vertex(eid.source, source_data)

            if eid.sink != ignore:
                sink_data = self._read_vertex(eid.sink)
                sink_data[SOURCES_INDEX].remove(eid.source)
                self._write_vertex(eid.sink, sink_data)
        else:
            assert isinstance(eid, base.UndirectedEdgeID)
            v1, v2 = eid.vertices

            if v1 != ignore:
                v1_data = self._read_vertex(v1)
                v1_data[UNDIRECTED_INDEX].remove(v2)
                self._write_vertex(v1, v1_data)

            if v1 != v2 and v2 != ignore:
                v2_data = self._read_vertex(v2)
                v2_data[UNDIRECTED_INDEX].remove(v2)
                self._write_vertex(v2, v2_data)

        self._e_count = self.count_edges() - 1
        self._e_count_dirty = True

        return True

    def add_vertex_label(self, vid: base.VertexID, label: base.Label) -> None:
        """Add a label to the vertex. If the vertex already has the label, do nothing."""
        self.add_vertex(vid)
        data = self._read_vertex(vid)
        if label not in data[LABEL_INDEX]:
            data[LABEL_INDEX].append(label)
            self._write_vertex(vid, data)

    def has_vertex_label(self, vid: base.VertexID, label: base.Label) -> bool:
        """Return a Boolean indicating whether the vertex has the label."""
        try:
            return label in self._read_vertex(vid)[LABEL_INDEX]
        except KeyError:
            return False

    def discard_vertex_label(self, vid: base.VertexID, label: base.Label) -> bool:
        """
        Remove the label from the vertex. If the vertex does not have the label, do nothing. Return a Boolean indicating
        whether or not a label was removed.
        """
        try:
            data = self._read_vertex(vid)
        except KeyError:
            return False
        if label in data[LABEL_INDEX]:
            data[LABEL_INDEX].remove(label)
            self._write_vertex(vid, data)
            return True
        return False

    def iter_vertex_labels(self, vid: base.VertexID) -> Iterator[base.Label]:
        """Return an iterator over the labels for the vertex."""
        try:
            return iter(self._read_vertex(vid)[LABEL_INDEX])
        except KeyError:
            return iter(())

    def count_vertex_labels(self, vid: base.VertexID) -> int:
        """Return the number of labels the vertex has."""
        try:
            return len(self._read_vertex(vid)[LABEL_INDEX])
        except KeyError:
            return 0

    def add_edge_label(self, eid: base.EdgeID, label: base.Label) -> None:
        """Add a label to the edge. If the edge already has the label, do nothing."""
        self.add_edge(eid)
        data = self._read_edge(eid)
        if label not in data[LABEL_INDEX]:
            data[LABEL_INDEX].append(label)
            self._write_edge(eid, data)

    def has_edge_label(self, eid: base.EdgeID, label: base.Label) -> bool:
        """Return a Boolean indicating whether or not the edge has the label."""
        try:
            return label in self._read_edge(eid)[LABEL_INDEX]
        except KeyError:
            return False

    def discard_edge_label(self, eid: base.EdgeID, label: base.Label) -> bool:
        """
        Remove the label from the edge. If the edge does not have the label, do nothing. Return a Boolean indicating
        whether or not a label was removed.
        """
        try:
            data = self._read_edge(eid)
        except KeyError:
            return False
        if label in data[LABEL_INDEX]:
            data[LABEL_INDEX].remove(label)
            self._write_edge(eid, data)
            return True
        return False

    def iter_edge_labels(self, eid: base.EdgeID) -> Iterator[base.Label]:
        """Return an iterator over the labels for the edge."""
        try:
            return iter(self._read_edge(eid)[LABEL_INDEX])
        except KeyError:
            return iter(())

    def count_edge_labels(self, eid: base.EdgeID) -> int:
        """Return the number of labels the edge has."""
        try:
            return len(self._read_edge(eid)[LABEL_INDEX])
        except KeyError:
            return 0

    def get_vertex_data(self, vid: base.VertexID, key: Hashable) -> Any:
        """Return the value stored in the vertex for this key."""
        try:
            return self._read_vertex(vid)[DATA_INDEX].get(key, None)
        except KeyError:
            return None

    def set_vertex_data(self, vid: base.VertexID, key: Hashable, value: Any) -> None:
        """Store a value in the vertex for this key."""
        self.add_vertex(vid)
        data = self._read_vertex(vid)
        data[DATA_INDEX][key] = value
        self._write_vertex(vid, data)

    def has_vertex_data(self, vid: base.VertexID, key: Hashable) -> bool:
        """Return a Boolean indicating whether a value is stored in the vertex for this key."""
        try:
            return key in self._read_vertex(vid)[DATA_INDEX]
        except KeyError:
            return False

    def discard_vertex_data(self, vid: base.VertexID, key: Hashable) -> bool:
        """
        Remove the value stored in the vertex under this key. If no value is stored for the key, do nothing. Return
        a Boolean indicating whether a key/value pair was removed from the vertex.
        """
        try:
            data = self._read_vertex(vid)
            del data[DATA_INDEX][key]
        except KeyError:
            return False
        else:
            self._write_vertex(vid, data)
            return True

    def iter_vertex_data_keys(self, vid: base.VertexID) -> Iterator[Hashable]:
        """Return an iterator over the keys for which data is stored in the vertex."""
        try:
            return iter(self._read_vertex(vid)[DATA_INDEX])
        except KeyError:
            return iter(())

    def count_vertex_data_keys(self, vid: base.VertexID) -> int:
        """Return the number of key/value pairs stored in the vertex."""
        try:
            return len(self._read_vertex(vid)[DATA_INDEX])
        except KeyError:
            return 0

    def get_edge_data(self, eid: base.EdgeID, key: Hashable) -> Any:
        """Return the value stored in the edge for this key."""
        try:
            return self._read_edge(eid)[DATA_INDEX][key]
        except KeyError:
            return None

    def set_edge_data(self, eid: base.EdgeID, key: Hashable, value: Any) -> None:
        """Store a value in the edge for this key."""
        self.add_edge(eid)
        data = self._read_edge(eid)
        data[DATA_INDEX][key] = value
        self._write_edge(eid, data)

    def has_edge_data(self, eid: base.EdgeID, key: Hashable) -> bool:
        """Return a Boolean indicating whether a value is stored in the edge for this key."""
        try:
            return key in self._read_edge(eid)[DATA_INDEX]
        except KeyError:
            return False

    def discard_edge_data(self, eid: base.EdgeID, key: Hashable) -> bool:
        """
        Remove the value stored in the edge under this key. If no value is stored for the key, do nothing. Return
        a Boolean indicating whether a key/value pair was removed from the edge.
        """
        try:
            data = self._read_edge(eid)
            del data[DATA_INDEX][key]
        except KeyError:
            return False
        else:
            self._write_edge(eid, data)
            return True

    def iter_edge_data_keys(self, eid: base.EdgeID) -> Iterator[Hashable]:
        """Return an iterator over the keys for which data is stored in the edge."""
        try:
            return iter(self._read_edge(eid)[DATA_INDEX])
        except KeyError:
            return iter(())

    def count_edge_data_keys(self, eid: base.EdgeID) -> int:
        """Return the number of key/value pairs stored in the edge."""
        try:
            return len(self._read_edge(eid)[DATA_INDEX])
        except KeyError:
            return 0
