import unittest
from ledger import Ledger
from sender import Sender

class Public(unittest.TestCase):
    def test_exact_duplicate_is_deduplicated(self):
        sender = Sender(Ledger())
        operation = {"event_id": "e1", "tenant": "a", "recipient": "r", "amount": 5, "version": 1}
        changed = {"event_id": "e1", "tenant": "a", "recipient": "r", "amount": 6, "version": 1}
        sender.send(operation)
        sender.send(changed)
        self.assertEqual(len(sender.sent), 2)
