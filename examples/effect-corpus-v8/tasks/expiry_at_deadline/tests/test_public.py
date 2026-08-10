import unittest
from expiry import expired

class Public(unittest.TestCase):
    def test_deadline_is_already_expired(self):
        self.assertTrue(expired(110, 100, 10))
