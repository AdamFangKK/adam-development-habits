import unittest
from assign import visible

class Public(unittest.TestCase):
    def test_assignment_is_tenant_scoped(self):
        self.assertTrue(visible("acme", "alice"))
        self.assertFalse(visible("globex", "alice"))
