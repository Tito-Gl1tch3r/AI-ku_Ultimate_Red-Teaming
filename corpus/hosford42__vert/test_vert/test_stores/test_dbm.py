# -*- coding: utf-8 -*-

# Copyright 2017 Aaron M. Hosford
# See LICENSE.txt for licensing information.

import os
import unittest

from vert.stores.dbm import DBMGraphStore
from vert import Graph

# noinspection PyProtectedMember
import test_vert.test_stores._base as _base


class TestDBMGraphStore(_base.TestGraphStore):

    @property
    def graph(self):
        # noinspection PyProtectedMember
        store = self._graph._graph_store
        # noinspection PyProtectedMember
        self.assertEqual(store._v_cache_times.keys(), store._v_cache.keys())
        # noinspection PyProtectedMember
        self.assertLessEqual(store._v_cache_dirty, store._v_cache.keys())
        return self._graph

    def createStore(self):
        # noinspection PyAttributeOutsideInit
        self.path = 'test1.db'
        if os.path.isfile(self.path):
            os.remove(self.path)
        return self.path

    def expectedStoreClass(self):
        return DBMGraphStore

    def tearDown(self):
        super().tearDown()
        graph = getattr(self, 'graph', None)
        if graph:
            # noinspection PyProtectedMember
            graph._graph_store.close()
        path = getattr(self, 'path', None)
        if path and os.path.isfile(path):
            os.remove(path)


class TestDBMGraphStoreNoCache(_base.TestGraphStore):

    @property
    def graph(self):
        # noinspection PyProtectedMember
        store = self._graph._graph_store
        # noinspection PyProtectedMember
        self.assertEqual(store._v_cache_times.keys(), store._v_cache.keys())
        # noinspection PyProtectedMember
        self.assertLessEqual(store._v_cache_dirty, store._v_cache.keys())
        return self._graph

    def createStore(self):
        # noinspection PyAttributeOutsideInit
        self.path = 'test2.db'
        if os.path.isfile(self.path):
            os.remove(self.path)
        return self.path

    def expectedStoreClass(self):
        return DBMGraphStore

    def setUp(self):
        super().setUp()
        # noinspection PyProtectedMember
        self._graph._graph_store.vertex_cache_size = 0
        # noinspection PyProtectedMember
        self._graph._graph_store.edge_cache_size = 0

    def tearDown(self):
        super().tearDown()
        graph = getattr(self, 'graph', None)
        if graph:
            # noinspection PyProtectedMember
            graph._graph_store.close()
        path = getattr(self, 'path', None)
        if path and os.path.isfile(path):
            os.remove(path)


class TestDBMGraphStorePersistence(unittest.TestCase):

    def setUp(self):
        self.path = 'test3.db'

    def testPersistence(self):
        with Graph(self.path) as graph:
            self.assert_(graph.is_open)
            self.assert_(not graph.edges[1, 2])
            self.assert_(not graph.edges[2, 3])
            self.assert_(not graph.edges[1, 3])
            self.assert_(not graph.edges[3, 4])
            graph.edges[1, 2].add()
            graph.edges[2, 3].add()
            graph.edges[1, 3].add()
            graph.edges[3, 4].add()
            self.assert_(graph.edges[1, 2])
            self.assert_(graph.edges[2, 3])
            self.assert_(graph.edges[1, 3])
            self.assert_(graph.edges[3, 4])
        self.assert_(not graph.is_open)

        with Graph(self.path) as graph:
            self.assert_(graph.is_open)
            self.assert_(graph.edges[1, 2])
            self.assert_(graph.edges[2, 3])
            self.assert_(graph.edges[1, 3])
            self.assert_(graph.edges[3, 4])
            graph.edges[3, 4].remove()
            self.assert_(graph.edges[1, 2])
            self.assert_(graph.edges[2, 3])
            self.assert_(graph.edges[1, 3])
            self.assert_(not graph.edges[3, 4])
        self.assert_(not graph.is_open)

        with Graph(self.path) as graph:
            self.assert_(graph.is_open)
            self.assert_(graph.edges[1, 2])
            self.assert_(graph.edges[2, 3])
            self.assert_(graph.edges[1, 3])
            self.assert_(not graph.edges[3, 4])
            self.assertEqual(len(graph.vertices), 4)
            self.assertEqual(len(graph.edges), 3)

        self.assert_(not graph.is_open)

    def tearDown(self):
        if os.path.isfile(self.path):
            os.remove(self.path)
