import unittest
from assign import visible

class Hidden(unittest.TestCase):
    def test_same_user_can_differ_by_tenant(self):
        self.assertTrue(visible("acme", "alice"))
        self.assertFalse(visible("globex", "alice"))
        self.assertFalse(visible("acme", "bob"))
