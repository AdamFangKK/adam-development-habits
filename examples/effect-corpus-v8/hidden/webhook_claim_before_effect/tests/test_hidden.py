import unittest
from nonces import Nonces
from receiver import receive

class Hidden(unittest.TestCase):
    def test_success_is_also_idempotent(self):
        effects = []
        def handler(event):
            effects.append(event["id"])
        nonces = Nonces()
        event = {"id": "evt2", "nonce": "n2"}
        self.assertEqual(receive(event, nonces, handler), "ok")
        self.assertEqual(receive(event, nonces, handler), "duplicate")
        self.assertEqual(effects, ["evt2"])
