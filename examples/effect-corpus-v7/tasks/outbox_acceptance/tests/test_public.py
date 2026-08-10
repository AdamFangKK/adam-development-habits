import unittest
from store import Store
from worker import handle

class Provider:
    def send(self, event):
        return "sent"

class Public(unittest.TestCase):
    def test_ack_has_durable_record(self):
        store = Store()
        self.assertEqual(handle({"id": "e1"}, Provider(), store), "ack")
        self.assertEqual(store.events, [{"id": "e1"}])
