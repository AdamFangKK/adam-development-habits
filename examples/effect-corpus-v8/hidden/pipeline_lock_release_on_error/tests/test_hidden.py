import unittest
from lock import Lock
from runner import run

class Hidden(unittest.TestCase):
    def test_success_releases_and_allows_next_run(self):
        lock = Lock()
        self.assertEqual(run(lock, lambda: "ok"), "ok")
        self.assertFalse(lock.held)
        self.assertEqual(run(lock, lambda: "again"), "again")
