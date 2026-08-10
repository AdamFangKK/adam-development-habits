import unittest
from snapshot import Snapshot
from store import Store

class Hidden(unittest.TestCase):
    def test_update_invalidates_snapshot(self):
        store = Store("old")
        snapshot = Snapshot(store)
        self.assertEqual(snapshot.read(), "old")
        store.update("new")
        self.assertEqual(snapshot.read(), "new")
