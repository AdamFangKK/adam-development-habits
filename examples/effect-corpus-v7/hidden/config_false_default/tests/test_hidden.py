import unittest
from settings import enabled

class Hidden(unittest.TestCase):
    def test_missing_and_false_are_distinct(self):
        self.assertTrue(enabled({}))
        self.assertFalse(enabled({"enabled": 0}))
        self.assertTrue(enabled({"enabled": "yes"}))
