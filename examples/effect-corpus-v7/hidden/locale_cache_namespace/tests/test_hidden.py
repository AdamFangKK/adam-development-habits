import unittest
from catalog import Catalog

class Hidden(unittest.TestCase):
    def test_warm_cache_isolated_in_both_directions(self):
        catalog = Catalog({("en", "open"): "Open", ("de", "open"): "Öffnen"})
        self.assertEqual(catalog.label("de", "open"), "Öffnen")
        self.assertEqual(catalog.label("en", "open"), "Open")
        self.assertEqual(catalog.label("de", "open"), "Öffnen")
