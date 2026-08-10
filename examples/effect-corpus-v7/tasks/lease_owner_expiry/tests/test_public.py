import unittest
from lease import Lease
from worker import heartbeat

class Public(unittest.TestCase):
    def test_only_owner_can_renew(self):
        lease = Lease()
        self.assertTrue(lease.acquire("alice", 0, 10))
        with self.assertRaises(PermissionError):
            heartbeat(lease, "bob", 1, 10)
