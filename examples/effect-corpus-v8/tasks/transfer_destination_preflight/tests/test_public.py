import unittest
from inventory import Inventory
from transfer import transfer

class Public(unittest.TestCase):
    def test_rejected_transfer_keeps_source_stock(self):
        source = Inventory({"widget": 5}, 10)
        destination = Inventory({"other": 9}, 10)
        with self.assertRaises(OverflowError):
            transfer(source, destination, "widget", 2)
        self.assertEqual(source.quantity("widget"), 5)
