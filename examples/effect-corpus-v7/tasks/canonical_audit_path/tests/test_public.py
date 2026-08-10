import unittest
from audit import read_and_record

class Public(unittest.TestCase):
    def test_alias_audit_uses_canonical_path(self):
        _, event = read_and_record("alice", "/shortcut")
        self.assertEqual(event["resource"], "/documents/secret")
