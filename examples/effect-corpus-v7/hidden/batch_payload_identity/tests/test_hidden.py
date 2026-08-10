import unittest
from batch import deliver
from ledger import Ledger

class Hidden(unittest.TestCase):
    def test_exact_duplicate_only_is_reused(self):
        calls = []
        def send(event):
            calls.append(event["payload"])
            return len(calls)
        ledger = Ledger()
        event = {"event_id": "e", "payload": "same"}
        self.assertEqual(deliver(ledger, event, send), 1)
        self.assertEqual(deliver(ledger, dict(event), send), 1)
        self.assertEqual(deliver(ledger, {"event_id": "e", "payload": "other"}, send), 2)
        self.assertEqual(calls, ["same", "other"])
