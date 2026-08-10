import unittest
from audit import read_and_record

class Hidden(unittest.TestCase):
    def test_direct_and_alias_events_are_canonical(self):
        _, alias_event = read_and_record("alice", "/shortcut")
        _, direct_event = read_and_record("alice", "/documents/secret")
        self.assertEqual(alias_event, direct_event)
