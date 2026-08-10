import unittest
from dispatcher import Dispatcher
from provider import Provider

class Hidden(unittest.TestCase):
    def test_accepted_timeout_stays_pending_without_duplicate(self):
        provider = Provider("accepted-timeout")
        self.assertEqual(Dispatcher(provider).deliver({"id": "op-9"}), "pending")
        self.assertEqual(provider.accepted, ["op-9"])
