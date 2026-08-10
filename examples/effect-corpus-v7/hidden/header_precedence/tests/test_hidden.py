import unittest
from loader import load

class Hidden(unittest.TestCase):
    def test_precedence_and_falsey_values(self):
        self.assertEqual(load("", "env", "file"), "")
        self.assertEqual(load(None, "env", "file"), "env")
        self.assertEqual(load(None, None, "file"), "file")
