import unittest
from store import Store
from worker import handle

class AcceptedThenTimeout:
    def send(self, event):
        raise TimeoutError("provider result unknown")

class PublicProvider:
    def send(self, event):
        return "sent"

class Hidden(unittest.TestCase):
    def test_unknown_result_is_pending_and_not_ack(self):
        store = Store()
        self.assertEqual(handle({"id": "e2"}, AcceptedThenTimeout(), store), "pending")
        self.assertEqual(store.events, [])
        self.assertEqual(handle({"id": "e3"}, PublicProvider(), store), "ack")
        self.assertEqual(store.events, [{"id": "e3"}])
