import unittest
from roles import Checker, RoleStore

class Public(unittest.TestCase):
    def test_granted_role(self):
        store = RoleStore()
        checker = Checker(store)
        self.assertTrue(checker.has_role("alice", "reader"))
        store.revoke("alice", "reader")
        self.assertFalse(checker.has_role("alice", "reader"))
