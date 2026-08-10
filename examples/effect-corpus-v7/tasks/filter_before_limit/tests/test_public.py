import unittest
from repository import query

class Public(unittest.TestCase):
    def test_filter_is_applied_before_limit(self):
        rows = [{"id": 1, "status": "closed"}, {"id": 2, "status": "open"}]
        self.assertEqual(query(rows, "open", 1), [{"id": 2, "status": "open"}])
