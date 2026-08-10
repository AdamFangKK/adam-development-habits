import unittest
from rounding import cents

class Hidden(unittest.TestCase):
    def test_both_even_and_odd_ties(self):
        self.assertEqual(cents("2.345"), 2.34)
        self.assertEqual(cents("2.355"), 2.36)
        self.assertEqual(cents("2.346"), 2.35)
