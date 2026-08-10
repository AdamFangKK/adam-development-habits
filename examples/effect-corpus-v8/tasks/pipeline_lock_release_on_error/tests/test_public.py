import unittest
from lock import Lock
from runner import run

class Public(unittest.TestCase):
    def test_exception_releases_lock(self):
        lock = Lock()
        def step():
            raise RuntimeError("boom")
        with self.assertRaises(RuntimeError):
            run(lock, step)
        self.assertFalse(lock.held)
