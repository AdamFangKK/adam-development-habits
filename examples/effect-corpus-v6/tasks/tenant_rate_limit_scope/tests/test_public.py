import unittest
from limiter import Limiter

class Public(unittest.TestCase):
    def test_one_user_limit(self):
        limiter = Limiter(1)
        self.assertTrue(limiter.allow("acme", "u1"))
        self.assertTrue(limiter.allow("globex", "u1"))
