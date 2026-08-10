import unittest
from dispatcher import Dispatcher
from provider import Provider

class Public(unittest.TestCase):
    def test_pre_acceptance_rejection_can_retry(self):
        provider = Provider("accepted-timeout")
        self.assertEqual(Dispatcher(provider).deliver({"id": "op-1"}), "pending")
        self.assertEqual(provider.accepted, ["op-1"])
