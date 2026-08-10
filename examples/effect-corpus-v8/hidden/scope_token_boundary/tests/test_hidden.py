import unittest
from scopes import has_scope

class Hidden(unittest.TestCase):
    def test_exact_scope_is_required(self):
        self.assertTrue(has_scope({"scope": "read write"}, "read"))
        self.assertFalse(has_scope({"scope": "read:all"}, "read"))
        self.assertFalse(has_scope({}, "read"))
