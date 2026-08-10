import unittest
from checkout import purchase
from quota import Quota

def declines(amount):
    raise RuntimeError("declined")

class Public(unittest.TestCase):
    def test_failed_payment_restores_quota(self):
        quota = Quota(10)
        self.assertEqual(purchase(quota, declines, 4), "failed")
        self.assertEqual(quota.available, 10)
