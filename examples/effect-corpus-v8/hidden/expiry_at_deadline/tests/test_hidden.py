import unittest
from expiry import expired

class Hidden(unittest.TestCase):
    def test_before_after_and_zero_ttl(self):
        self.assertFalse(expired(109, 100, 10))
        self.assertTrue(expired(111, 100, 10))
        self.assertTrue(expired(5, 5, 0))
