import unittest
from repository import query

class Hidden(unittest.TestCase):
    def test_limit_is_on_matching_rows_and_none_keeps_all(self):
        rows = [{"id": 1, "status": "closed"}, {"id": 2, "status": "open"}, {"id": 3, "status": "open"}]
        self.assertEqual([row["id"] for row in query(rows, "open", 1)], [2])
        self.assertEqual([row["id"] for row in query(rows, None, 2)], [1, 2])
