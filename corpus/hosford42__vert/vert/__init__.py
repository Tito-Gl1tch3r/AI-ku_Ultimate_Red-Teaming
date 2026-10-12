# -*- coding: utf-8 -*-

# Copyright 2017 Aaron M. Hosford
# See LICENSE.txt for licensing information.


"""
Vert
====

Vert is a Python package which attempts to provide a standardized interface for graphs. It does so by separating the
graph into two separate layers of abstraction:

* The graph store: This is where the graph is actually stored and represented. It may be a graph database, another graph
  library's data structure, or one of vert's built-in graph store objects.
* The graph interface: This is where you, the programmer, can access the graph via an intuitive object-oriented
  interface using familiar data types such as Graph, Vertex, and Edge.

Because vert is structured along these distinct layers of abstraction, it is possible to write code that utilizes
and operates on a graph without regard for the underlying storage mechanisms. Storage mechanisms can be freely swapped
out for each other at the point where the graph object is initialized, and, aside from differences in performance and
persistence, the rest of your code will never know the difference. Support for new graph storage mechanisms can be
added simply by creating a class that supports the GraphStore interface. This means you never have to worry about vendor
lock-in, and updating your code to use the latest technology is as simple as a one-line change.
"""


from . import stores, graphs

from .stores.base import GraphStore, VertexID, EdgeID, DirectedEdgeID, UndirectedEdgeID, Label
from .stores.dbm import DBMGraphStore
from .stores.memory import MemoryGraphStore
from .graphs import Graph, Vertex, Edge, DirectedEdge, UndirectedEdge

from .__about__ import __title__, __summary__, __url__, __version__, __status__, __author__, __maintainer__, \
    __credits__, __email__, __license__, __copyright__


__all__ = [
    '__title__',
    '__summary__',
    '__url__',
    '__version__',
    '__status__',
    '__author__',
    '__maintainer__',
    '__credits__',
    '__email__',
    '__license__',
    '__copyright__',
    'stores',
    'graphs',
    'GraphStore',
    'VertexID',
    'EdgeID',
    'DirectedEdgeID',
    'UndirectedEdgeID',
    'Label',
    'DBMGraphStore',
    'MemoryGraphStore',
    'Graph',
    'Vertex',
    'Edge',
]
