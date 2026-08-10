import unittest
from resource_service import read

class Hidden(unittest.TestCase):
    def test_alias_uses_canonical_authorization(self):
        with self.assertRaises(PermissionError):
            read("alice", "alias")
        self.assertEqual(read("admin", "alias"), "classified")
