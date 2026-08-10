import unittest
from batch import Batch, Store

class Hidden(unittest.TestCase):
    def test_retry_does_not_duplicate_partial_rows(self):
        store = Store(fail_at=1)
        batch = Batch(store)
        self.assertEqual(batch.process(["a", "b"]), "retry")
        store.fail_at = None
        self.assertEqual(batch.process(["a", "b"]), "ok")
        self.assertEqual(store.rows, ["a", "b"])
