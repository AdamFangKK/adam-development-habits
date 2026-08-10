import unittest
from clock import Clock
from worker import run

def one(clock, deadline):
    clock.advance(2)
    if clock.now() > deadline:
        raise TimeoutError("dependency deadline")

def two(clock, deadline):
    clock.advance(2)
    if clock.now() > deadline:
        raise TimeoutError("dependency deadline")

class Hidden(unittest.TestCase):
    def test_budget_is_shared_and_exact_boundary_is_allowed(self):
        with self.assertRaises(TimeoutError):
            run([one, two, one], Clock(), 5)
        self.assertEqual(run([one, two], Clock(), 4), "ok")
