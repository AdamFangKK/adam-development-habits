import unittest
from limiter import Limiter

class Hidden(unittest.TestCase):
    def test_tenants_are_isolated(self):
        limiter = Limiter(1)
        self.assertTrue(limiter.allow("acme", "u1"))
        self.assertTrue(limiter.allow("globex", "u1"))
