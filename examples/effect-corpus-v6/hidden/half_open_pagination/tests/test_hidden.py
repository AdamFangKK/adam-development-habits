import unittest
from pager import page

class Hidden(unittest.TestCase):
    def test_empty_and_last_boundaries(self):
        self.assertEqual(page(["a", "b", "c"], 1, 1), [])
        self.assertEqual(page(["a", "b", "c"], 2, 3), ["c"])
