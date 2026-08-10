import unittest
from billing import total

class Public(unittest.TestCase):
    def test_whole_cent_invoice(self):
        self.assertEqual(str(total([("0.335", 1)], "0.05")), "0.35")
