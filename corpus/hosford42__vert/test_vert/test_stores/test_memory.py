# -*- coding: utf-8 -*-

# Copyright 2017 Aaron M. Hosford
# See LICENSE.txt for licensing information.

from vert.stores.memory import MemoryGraphStore

# noinspection PyProtectedMember
import test_vert.test_stores._base as _base


class TestMemoryGraphStore(_base.TestGraphStore):

    def createStore(self):
        return None  # Default

    def expectedStoreClass(self):
        return MemoryGraphStore
