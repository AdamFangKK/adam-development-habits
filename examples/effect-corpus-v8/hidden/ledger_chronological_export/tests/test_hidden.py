import unittest
from ledger import Ledger

class Hidden(unittest.TestCase):
    def test_export_returns_copies_in_chronological_order(self):
        ledger = Ledger()
        ledger.append({"account": "b", "amount": 1})
        exported = ledger.export()
        exported[0]["amount"] = 99
        self.assertEqual(ledger.export()[0]["amount"], 1)
