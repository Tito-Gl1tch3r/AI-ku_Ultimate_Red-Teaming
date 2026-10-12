# -*- coding: utf-8 -*-

# Copyright 2017 Aaron M. Hosford
# See LICENSE.txt for licensing information.

from typing import Type

import unittest


from vert import Graph, GraphStore, Vertex, Edge, DirectedEdge


class TestGraphStore(unittest.TestCase):

    def createStore(self) -> GraphStore:
        raise NotImplementedError()

    def expectedStoreClass(self) -> Type[GraphStore]:
        raise NotImplementedError()

    def setUp(self):
        # The failure messages don't work properly when they're done in a base class, making this necessary.
        print("Setting up %s" % self)
        super().setUp()
        self._graph = Graph(self.createStore())

    def tearDown(self):
        # The failure messages don't work properly when they're done in a base class, making this necessary.
        print("Tearing down %s" % self)
        super().tearDown()

    @property
    def graph(self):
        return self._graph

    def testDefaultStoreClass(self):
        self.assertIsInstance(self.graph._graph_store, self.expectedStoreClass())

    def testVertexCreationAndDeletion(self):
        vertex_name = 'v1'
        vertex = self.graph.vertices[vertex_name]
        self.assertEqual(vertex.vid, vertex_name)
        self.assertIsInstance(vertex, Vertex)
        self.assert_(not vertex.exists)
        self.assertEqual(len(self.graph.vertices), 0)
        vertex.add()
        self.assertEqual(len(self.graph.vertices), 1)
        self.assert_(vertex.exists)
        vertex.remove()
        self.assertEqual(len(self.graph.vertices), 0)
        self.assert_(not vertex.exists)
        vertex2 = self.graph.vertices.add(vertex_name)
        self.assert_(vertex.exists)
        self.assert_(vertex2.exists)
        self.assertEqual(vertex, vertex2)
        self.assertEqual(vertex.vid, vertex2.vid)
        vertex2.remove()
        self.assert_(not vertex.exists)
        self.assert_(not vertex2.exists)

    def testVertexLabels(self):
        vertex_name = 'v2'
        label1_name = 'l1'
        label2_name = 'l2'
        vertex = self.graph.vertices[vertex_name]
        self.assertIsInstance(vertex, Vertex)
        self.assert_(not vertex.exists)
        self.assertEqual(len(vertex.labels), 0)
        self.assert_(not vertex.labels)
        vertex.labels.add(label1_name)
        self.assert_(vertex.exists)
        self.assert_(label1_name in vertex.labels)
        self.assert_(label2_name not in vertex.labels)
        self.assertEqual(len(vertex.labels), 1)
        self.assert_(vertex.labels)
        vertex.remove()
        self.assert_(not vertex.exists)
        self.assert_(not vertex.labels)
        self.assert_(label1_name not in vertex.labels)
        self.assert_(label2_name not in vertex.labels)
        self.graph.vertices.add(vertex_name)
        self.assert_(vertex.exists)
        self.assert_(label1_name not in vertex.labels)
        self.assert_(label2_name not in vertex.labels)
        vertex.labels.add(label2_name)
        self.assert_(label1_name not in vertex.labels)
        self.assert_(label2_name in vertex.labels)
        self.assertEqual(len(vertex.labels), 1)
        vertex.labels.add(label1_name)
        self.assert_(label1_name in vertex.labels)
        self.assert_(label2_name in vertex.labels)
        self.assertEqual(len(vertex.labels), 2)
        vertex.labels.remove(label2_name)
        self.assert_(label1_name in vertex.labels)
        self.assert_(label2_name not in vertex.labels)
        self.assertEqual(len(vertex.labels), 1)
        vertex.labels.discard(label2_name)
        self.assert_(label1_name in vertex.labels)
        self.assert_(label2_name not in vertex.labels)
        self.assertEqual(len(vertex.labels), 1)
        vertex.labels.discard(label1_name)
        self.assert_(label1_name not in vertex.labels)
        self.assert_(label2_name not in vertex.labels)
        self.assertEqual(len(vertex.labels), 0)
        vertex.remove()
        self.assertEqual(len(vertex.labels), 0)
        self.assert_(not vertex.labels)
        self.assert_(not vertex.exists)

    def testVertexData(self):
        vertex_name = 'v3'
        key1 = 'k1'
        key2 = 'k2'
        value1 = 'val1'
        value2 = 2
        value3 = {value1: value2}
        vertex = self.graph.vertices[vertex_name].add()
        self.assertIsInstance(vertex, Vertex)
        self.assert_(not vertex.data)
        with self.assertRaises(KeyError):
            _ = vertex.data[key1]
        with self.assertRaises(KeyError):
            _ = vertex.data[key2]
        self.assertEqual(len(vertex.data), 0)
        self.assertNotIn(key1, vertex.data)
        self.assertNotIn(key2, vertex.data)
        vertex.data[key1] = value1
        self.assert_(vertex.data)
        self.assertEqual(vertex.data[key1], value1)
        with self.assertRaises(KeyError):
            _ = vertex.data[key2]
        self.assertEqual(len(vertex.data), 1)
        self.assertIn(key1, vertex.data)
        self.assertNotIn(key2, vertex.data)
        vertex.data[key2] = value2
        self.assert_(vertex.data)
        self.assertEqual(vertex.data[key1], value1)
        self.assertEqual(vertex.data[key2], value2)
        self.assertEqual(len(vertex.data), 2)
        self.assertIn(key1, vertex.data)
        self.assertIn(key2, vertex.data)
        del vertex.data[key1]
        self.assert_(vertex.data)
        with self.assertRaises(KeyError):
            _ = vertex.data[key1]
        self.assertEqual(vertex.data[key2], value2)
        self.assertEqual(len(vertex.data), 1)
        self.assertNotIn(key1, vertex.data)
        self.assertIn(key2, vertex.data)
        vertex.data[key1] = value3
        self.assert_(vertex.data)
        self.assertEqual(vertex.data[key1], value3)
        self.assertEqual(vertex.data[key2], value2)
        self.assertEqual(len(vertex.data), 2)
        self.assertIn(key1, vertex.data)
        self.assertIn(key2, vertex.data)
        vertex.data[key2] = value3
        self.assert_(vertex.data)
        self.assertEqual(vertex.data[key1], value3)
        self.assertEqual(vertex.data[key2], value3)
        self.assertEqual(len(vertex.data), 2)
        self.assertIn(key1, vertex.data)
        self.assertIn(key2, vertex.data)
        vertex.data.clear()
        self.assert_(not vertex.data)
        with self.assertRaises(KeyError):
            _ = vertex.data[key1]
        with self.assertRaises(KeyError):
            _ = vertex.data[key2]
        self.assertEqual(len(vertex.data), 0)
        self.assertNotIn(key1, vertex.data)
        self.assertNotIn(key2, vertex.data)

    def testEdgeCreationAndDeletion(self):
        vid1 = 'v4'
        vid2 = 'v5'
        eid = (vid1, vid2)
        edge = self.graph.edges[eid]
        self.assertIsInstance(edge, DirectedEdge)
        self.assertIsInstance(edge.source, Vertex)
        self.assertIsInstance(edge.sink, Vertex)
        self.assertEqual(edge.eid, eid)
        self.assertEqual(edge.source.vid, vid1)
        self.assertEqual(edge.sink.vid, vid2)
        self.assert_(not edge.exists)
        self.assert_(not edge.source.exists)
        self.assert_(not edge.sink.exists)
        self.assertEqual(len(self.graph.vertices), 0)
        self.assertEqual(len(self.graph.edges), 0)
        edge.add()
        self.assertEqual(len(self.graph.edges), 1)
        self.assertEqual(len(self.graph.vertices), 2)
        self.assert_(edge.exists)
        self.assert_(edge.source.exists)
        self.assert_(edge.sink.exists)
        edge.remove()
        self.assertEqual(len(self.graph.edges), 0)
        self.assertEqual(len(self.graph.vertices), 2)
        self.assert_(not edge.exists)
        self.assert_(edge.source.exists)
        self.assert_(edge.sink.exists)
        edge2 = self.graph.edges.add(eid)
        self.assert_(edge.exists)
        self.assert_(edge2.exists)
        self.assertEqual(edge, edge2)
        self.assertEqual(edge.eid, edge2.eid)
        edge2.remove()
        self.assert_(not edge.exists)
        self.assert_(not edge2.exists)

    def testEdgeLabels(self):
        vid1 = 'v6'
        vid2 = 'v7'
        eid = (vid1, vid2)
        label1_name = 'l1'
        label2_name = 'l2'
        edge = self.graph.edges[eid]
        self.assertIsInstance(edge, Edge)
        self.assert_(not edge.exists)
        self.assertEqual(len(edge.labels), 0)
        self.assert_(not edge.labels)
        edge.labels.add(label1_name)
        self.assert_(edge.exists)
        self.assert_(label1_name in edge.labels)
        self.assert_(label2_name not in edge.labels)
        self.assertEqual(len(edge.labels), 1)
        self.assert_(edge.labels)
        edge.remove()
        self.assert_(not edge.exists)
        self.assert_(not edge.labels)
        self.assert_(label1_name not in edge.labels)
        self.assert_(label2_name not in edge.labels)
        self.graph.edges.add(eid)
        self.assert_(edge.exists)
        self.assert_(label1_name not in edge.labels)
        self.assert_(label2_name not in edge.labels)
        edge.labels.add(label2_name)
        self.assert_(label1_name not in edge.labels)
        self.assert_(label2_name in edge.labels)
        self.assertEqual(len(edge.labels), 1)
        edge.labels.add(label1_name)
        self.assert_(label1_name in edge.labels)
        self.assert_(label2_name in edge.labels)
        self.assertEqual(len(edge.labels), 2)
        edge.labels.remove(label2_name)
        self.assert_(label1_name in edge.labels)
        self.assert_(label2_name not in edge.labels)
        self.assertEqual(len(edge.labels), 1)
        edge.labels.discard(label2_name)
        self.assert_(label1_name in edge.labels)
        self.assert_(label2_name not in edge.labels)
        self.assertEqual(len(edge.labels), 1)
        edge.labels.discard(label1_name)
        self.assert_(label1_name not in edge.labels)
        self.assert_(label2_name not in edge.labels)
        self.assertEqual(len(edge.labels), 0)
        edge.remove()
        self.assertEqual(len(edge.labels), 0)
        self.assert_(not edge.labels)
        self.assert_(not edge.exists)

    def testEdgeData(self):
        v1 = 'v8'
        v2 = 'v9'
        eid = (v1, v2)
        key1 = 'k1'
        key2 = 'k2'
        value1 = 'val1'
        value2 = 2
        value3 = {value1: value2}
        edge = self.graph.edges[eid].add()
        self.assertIsInstance(edge, Edge)
        self.assert_(not edge.data)
        with self.assertRaises(KeyError):
            _ = edge.data[key1]
        with self.assertRaises(KeyError):
            _ = edge.data[key2]
        self.assertEqual(len(edge.data), 0)
        self.assertNotIn(key1, edge.data)
        self.assertNotIn(key2, edge.data)
        edge.data[key1] = value1
        self.assert_(edge.data)
        self.assertEqual(edge.data[key1], value1)
        with self.assertRaises(KeyError):
            _ = edge.data[key2]
        self.assertEqual(len(edge.data), 1)
        self.assertIn(key1, edge.data)
        self.assertNotIn(key2, edge.data)
        edge.data[key2] = value2
        self.assert_(edge.data)
        self.assertEqual(edge.data[key1], value1)
        self.assertEqual(edge.data[key2], value2)
        self.assertEqual(len(edge.data), 2)
        self.assertIn(key1, edge.data)
        self.assertIn(key2, edge.data)
        del edge.data[key1]
        self.assert_(edge.data)
        with self.assertRaises(KeyError):
            _ = edge.data[key1]
        self.assertEqual(edge.data[key2], value2)
        self.assertEqual(len(edge.data), 1)
        self.assertNotIn(key1, edge.data)
        self.assertIn(key2, edge.data)
        edge.data[key1] = value3
        self.assert_(edge.data)
        self.assertEqual(edge.data[key1], value3)
        self.assertEqual(edge.data[key2], value2)
        self.assertEqual(len(edge.data), 2)
        self.assertIn(key1, edge.data)
        self.assertIn(key2, edge.data)
        edge.data[key2] = value3
        self.assert_(edge.data)
        self.assertEqual(edge.data[key1], value3)
        self.assertEqual(edge.data[key2], value3)
        self.assertEqual(len(edge.data), 2)
        self.assertIn(key1, edge.data)
        self.assertIn(key2, edge.data)
        edge.data.clear()
        self.assert_(not edge.data)
        with self.assertRaises(KeyError):
            _ = edge.data[key1]
        with self.assertRaises(KeyError):
            _ = edge.data[key2]
        self.assertEqual(len(edge.data), 0)
        self.assertNotIn(key1, edge.data)
        self.assertNotIn(key2, edge.data)
