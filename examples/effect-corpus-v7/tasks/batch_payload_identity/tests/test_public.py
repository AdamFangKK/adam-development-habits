import unittest
from batch import deliver
from ledger import Ledger

class Public(unittest.TestCase):
    def test_changed_payload_is_a_new_operation(self):
        calls = []
        def send(event):
            calls.append(event["payload"])
            return event["payload"]
        ledger = Ledger()
        self.assertEqual(deliver(ledger, {"event_id": "e", "payload": "one"}, send), "one")
        self.assertEqual(deliver(ledger, {"event_id": "e", "payload": "two"}, send), "two")
        self.assertEqual(calls, ["one", "two"])
