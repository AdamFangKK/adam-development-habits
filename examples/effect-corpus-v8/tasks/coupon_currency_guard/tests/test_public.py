import unittest
from checkout import total

class Public(unittest.TestCase):
    def test_coupon_currency_must_match_order_currency(self):
        with self.assertRaises(ValueError):
            total(100, "EUR", "SAVE10")
