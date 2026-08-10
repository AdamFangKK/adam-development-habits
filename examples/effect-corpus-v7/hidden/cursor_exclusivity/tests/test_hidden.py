import unittest
from pager import page

class Hidden(unittest.TestCase):
    def test_middle_empty_and_invalid_ranges(self):
        self.assertEqual(page(["a", "b", "c", "d"], 1, 3), ["b", "c"])
        self.assertEqual(page(["a"], 1, 1), [])
        with self.assertRaises(ValueError):
            page(["a"], 2, 1)
