import unittest
from inventory import Inventory
from transfer import transfer

class Hidden(unittest.TestCase):
    def test_success_moves_exact_amount(self):
        source = Inventory({"widget": 5}, 10)
        destination = Inventory({}, 10)
        self.assertEqual(transfer(source, destination, "widget", 3), "moved")
        self.assertEqual(source.quantity("widget"), 2)
        self.assertEqual(destination.quantity("widget"), 3)
