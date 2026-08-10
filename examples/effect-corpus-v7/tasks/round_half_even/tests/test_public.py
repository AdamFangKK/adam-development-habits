import unittest
from rounding import cents

class Public(unittest.TestCase):
    def test_tie_rounds_to_even(self):
        self.assertEqual(cents("2.345"), 2.34)
