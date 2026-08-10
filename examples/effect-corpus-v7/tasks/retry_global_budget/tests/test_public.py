import unittest
from clock import Clock
from worker import run

def slow(clock, deadline):
    clock.advance(3)
    if clock.now() > deadline:
        raise TimeoutError("dependency deadline")

class Public(unittest.TestCase):
    def test_one_global_budget(self):
        with self.assertRaises(TimeoutError):
            run([slow, slow], Clock(), 5)
