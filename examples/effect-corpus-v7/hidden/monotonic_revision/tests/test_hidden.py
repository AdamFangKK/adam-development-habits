import unittest
from consumer import consume
from store import Store

class Hidden(unittest.TestCase):
    def test_duplicate_and_stale_updates_are_ignored(self):
        events = [{"revision": 3, "value": "x"}, {"revision": 3, "value": "wrong"}, {"revision": 2, "value": "old"}]
        self.assertEqual(consume(Store(), events), (3, "x"))
