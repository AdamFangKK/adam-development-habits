import unittest
from consumer import consume
from store import Store

class Public(unittest.TestCase):
    def test_stale_update_is_ignored(self):
        events = [{"revision": 2, "value": "new"}, {"revision": 1, "value": "old"}]
        self.assertEqual(consume(Store(), events), (2, "new"))
