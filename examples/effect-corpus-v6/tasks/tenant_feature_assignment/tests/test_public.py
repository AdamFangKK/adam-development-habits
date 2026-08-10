import unittest
from flags import enabled

class Public(unittest.TestCase):
    def test_key_is_stable_for_one_tenant(self):
        self.assertEqual(enabled("acme", "u1"), "acme:u1")
