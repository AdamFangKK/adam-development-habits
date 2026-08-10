import unittest
from scopes import has_scope

class Public(unittest.TestCase):
    def test_scope_must_match_a_token_boundary(self):
        self.assertFalse(has_scope({"scope": "bread write"}, "read"))
