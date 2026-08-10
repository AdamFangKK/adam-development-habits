import unittest
from retrying import Clock, run

class Public(unittest.TestCase):
    def test_success_does_not_retry(self):
        attempts = [0]

        def work():
            attempts[0] += 1
            if attempts[0] < 3:
                raise TimeoutError()
            return "ok"

        self.assertEqual(run(work, Clock([0, 4, 5, 6])), "timed_out")
