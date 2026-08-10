import unittest
from pager import page

class Public(unittest.TestCase):
    def test_end_cursor_is_exclusive(self):
        self.assertEqual(page(["a", "b", "c"], 0, 2), ["a", "b"])
