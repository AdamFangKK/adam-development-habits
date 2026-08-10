import unittest
from checksums import digest

class Hidden(unittest.TestCase):
    def test_equal_records_match_and_order_still_matters(self):
        self.assertEqual(digest(["x", ""]), digest(["x", ""]))
        self.assertNotEqual(digest(["x", "y"]), digest(["y", "x"]))
