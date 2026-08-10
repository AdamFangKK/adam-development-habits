import unittest
from settings import enabled

class Public(unittest.TestCase):
    def test_explicit_false_is_preserved(self):
        self.assertFalse(enabled({"enabled": False}))
