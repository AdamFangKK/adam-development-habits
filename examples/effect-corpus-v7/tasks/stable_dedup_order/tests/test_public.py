import unittest
from dedup import unique

class Public(unittest.TestCase):
    def test_first_occurrence_order(self):
        self.assertEqual(unique(["b", "a", "b", "c"]), ["b", "a", "c"])
