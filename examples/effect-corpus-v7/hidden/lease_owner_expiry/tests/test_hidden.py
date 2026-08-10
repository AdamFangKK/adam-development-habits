import unittest
from lease import Lease
from worker import heartbeat

class Hidden(unittest.TestCase):
    def test_owner_and_expiry_boundaries(self):
        lease = Lease()
        self.assertTrue(lease.acquire("alice", 0, 10))
        self.assertTrue(heartbeat(lease, "alice", 5, 10))
        with self.assertRaises(PermissionError):
            heartbeat(lease, "bob", 6, 10)
        lease.expires = 6
        with self.assertRaises(PermissionError):
            heartbeat(lease, "alice", 6, 10)
