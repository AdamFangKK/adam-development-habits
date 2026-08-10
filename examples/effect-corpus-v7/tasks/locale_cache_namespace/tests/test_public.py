import unittest
from catalog import Catalog

class Public(unittest.TestCase):
    def test_locales_do_not_share_labels(self):
        catalog = Catalog({("en", "save"): "Save", ("fr", "save"): "Enregistrer"})
        self.assertEqual(catalog.label("en", "save"), "Save")
        self.assertEqual(catalog.label("fr", "save"), "Enregistrer")
