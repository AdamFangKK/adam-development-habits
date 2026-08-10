import unittest
from catalog import Catalog

class Public(unittest.TestCase):
    def test_same_tenant_cache(self):
        catalog = Catalog({("acme", "basic"): 10, ("globex", "basic"): 90})
        self.assertEqual(catalog.price("acme", "basic"), 10)
        self.assertEqual(catalog.price("globex", "basic"), 90)
