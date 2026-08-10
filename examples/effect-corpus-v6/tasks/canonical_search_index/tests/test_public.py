import unittest
from index import Index

class Public(unittest.TestCase):
    def test_ascii_search(self):
        index = Index()
        index.add("Ｆoo", "doc-1")
        self.assertEqual(index.search("foo"), ["doc-1"])
