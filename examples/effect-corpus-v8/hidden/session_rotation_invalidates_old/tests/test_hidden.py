import unittest
from auth import authorized, login
from tokens import Tokens

class Hidden(unittest.TestCase):
    def test_rotation_is_per_user(self):
        tokens = Tokens()
        login(tokens, "u1", "old")
        login(tokens, "u2", "other")
        login(tokens, "u1", "new")
        self.assertFalse(authorized(tokens, "u1", "old"))
        self.assertTrue(authorized(tokens, "u2", "other"))
