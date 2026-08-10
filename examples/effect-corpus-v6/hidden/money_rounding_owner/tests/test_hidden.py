import unittest
from billing import total

class Hidden(unittest.TestCase):
    def test_rounding_happens_after_tax(self):
        self.assertEqual(total([("0.335", 1)], "0.10"), total([("0.335", 1)], "0.10"))
        self.assertEqual(str(total([("0.335", 1)], "0.10")), "0.37")
