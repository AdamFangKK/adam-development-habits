import unittest
from checkout import purchase
from quota import Quota

def declines(amount):
    raise RuntimeError("declined")

def accepts(amount):
    return "ok"

class Hidden(unittest.TestCase):
    def test_failure_release_and_success_consumption(self):
        quota = Quota(10)
        self.assertEqual(purchase(quota, declines, 4), "failed")
        self.assertEqual(quota.available, 10)
        self.assertEqual(purchase(quota, accepts, 6), "paid")
        self.assertEqual(quota.available, 4)
