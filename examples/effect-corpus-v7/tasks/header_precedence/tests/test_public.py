import unittest
from loader import load

class Public(unittest.TestCase):
    def test_explicit_cli_wins(self):
        self.assertEqual(load("debug", "production", "file"), "debug")
