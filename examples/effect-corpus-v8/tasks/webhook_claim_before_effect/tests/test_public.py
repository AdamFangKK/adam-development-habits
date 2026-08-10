import unittest
from nonces import Nonces
from receiver import receive

class Public(unittest.TestCase):
    def test_partial_failure_does_not_replay_effect(self):
        effects = []
        def handler(event):
            effects.append(event["id"])
            raise RuntimeError("after effect")
        nonces = Nonces()
        event = {"id": "evt1", "nonce": "n1"}
        self.assertEqual(receive(event, nonces, handler), "failed")
        self.assertEqual(receive(event, nonces, handler), "duplicate")
        self.assertEqual(effects, ["evt1"])
