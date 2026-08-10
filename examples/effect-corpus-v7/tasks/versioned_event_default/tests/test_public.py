import unittest
from consumer import decode

class Public(unittest.TestCase):
    def test_missing_version_uses_legacy_shape(self):
        self.assertEqual(decode({"name": "x", "enabled": 1}), {"name": "x", "active": True})
