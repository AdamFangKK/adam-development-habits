import unittest
from auth import authorized, login
from tokens import Tokens

class Public(unittest.TestCase):
    def test_rotating_token_invalidates_old_token(self):
        tokens = Tokens()
        login(tokens, "u1", "old")
        login(tokens, "u1", "new")
        self.assertFalse(authorized(tokens, "u1", "old"))
        self.assertTrue(authorized(tokens, "u1", "new"))
