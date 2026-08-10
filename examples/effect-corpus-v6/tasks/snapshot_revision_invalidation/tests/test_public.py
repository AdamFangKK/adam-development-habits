import unittest
from snapshot import Snapshot
from store import Store

class Public(unittest.TestCase):
    def test_initial_snapshot(self):
        store = Store("old")
        snapshot = Snapshot(store)
        self.assertEqual(snapshot.read(), "old")
        store.update("new")
        self.assertEqual(snapshot.read(), "new")
