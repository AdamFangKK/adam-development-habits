import unittest
from batch import Batch, Store

class Public(unittest.TestCase):
    def test_successful_batch(self):
        store = Store(fail_at=1)
        self.assertEqual(Batch(store).process(["a", "b"]), "retry")
        self.assertEqual(store.rows, [])
