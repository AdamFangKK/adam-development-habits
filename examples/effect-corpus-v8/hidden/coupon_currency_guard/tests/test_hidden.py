import unittest
from checkout import total

class Hidden(unittest.TestCase):
    def test_matching_coupon_and_no_coupon_paths(self):
        self.assertEqual(total(100, "USD", "SAVE10"), 90)
        self.assertEqual(total(100, "EUR"), 100)
