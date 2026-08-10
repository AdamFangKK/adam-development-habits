import unittest
from ledger import Ledger

class Public(unittest.TestCase):
    def test_export_keeps_append_order(self):
        ledger = Ledger()
        ledger.append({"account": "b", "amount": 1})
        ledger.append({"account": "a", "amount": 2})
        self.assertEqual([entry["account"] for entry in ledger.export()], ["b", "a"])
