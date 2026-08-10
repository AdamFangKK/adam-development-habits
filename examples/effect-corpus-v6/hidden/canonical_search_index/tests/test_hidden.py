import unittest
from index import Index

class Hidden(unittest.TestCase):
    def test_write_and_read_share_canonical_form(self):
        index = Index()
        index.add("Ｆoo", "doc-1")
        index.add(" Café ", "doc-2")
        self.assertEqual(index.search("foo"), ["doc-1"])
        self.assertEqual(index.search("café"), ["doc-2"])
