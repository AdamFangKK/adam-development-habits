import unittest
from state import Store
from view import refresh

class Public(unittest.TestCase):
    def test_newer_revision_wins(self):
        store = Store()
        self.assertEqual(refresh(store, 2, {"mode": "new"}), (2, {"mode": "new"}))
        self.assertEqual(refresh(store, 1, {"mode": "old"}), (2, {"mode": "new"}))
