import unittest
from resource_service import read

class Public(unittest.TestCase):
    def test_public_resource(self):
        self.assertEqual(read("alice", "public"), "hello")
        self.assertEqual(read("admin", "alias"), "classified")
