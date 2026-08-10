import unittest
from ledger import Ledger
from sender import Sender

class Hidden(unittest.TestCase):
    def test_event_id_alone_is_not_identity(self):
        sender = Sender(Ledger())
        first = {"event_id": "e1", "tenant": "a", "recipient": "r", "amount": 5, "version": 1}
        second = {"event_id": "e1", "tenant": "b", "recipient": "r", "amount": 7, "version": 1}
        sender.send(first)
        self.assertEqual(sender.send(second)["amount"], 7)
        self.assertEqual(len(sender.sent), 2)
