import unittest
from catalog import Catalog

class Hidden(unittest.TestCase):
    def test_tenants_never_share_prices(self):
        catalog = Catalog({("acme", "basic"): 10, ("globex", "basic"): 90})
        self.assertEqual(catalog.price("acme", "basic"), 10)
        self.assertEqual(catalog.price("globex", "basic"), 90)
