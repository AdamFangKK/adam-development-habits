import unittest
from roles import Checker, RoleStore

class Hidden(unittest.TestCase):
    def test_revoke_invalidates_cached_authority(self):
        store = RoleStore()
        checker = Checker(store)
        self.assertTrue(checker.has_role("alice", "reader"))
        store.revoke("alice", "reader")
        self.assertFalse(checker.has_role("alice", "reader"))
