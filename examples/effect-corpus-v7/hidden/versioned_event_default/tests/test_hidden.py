import unittest
from consumer import decode

class Hidden(unittest.TestCase):
    def test_versions_and_unknown_schema(self):
        self.assertEqual(decode({"name": "x", "enabled": 0}), {"name": "x", "active": False})
        self.assertEqual(decode({"version": 2, "name": "x", "active": 1}), {"name": "x", "active": True})
        with self.assertRaises(ValueError):
            decode({"version": 9, "name": "x"})
