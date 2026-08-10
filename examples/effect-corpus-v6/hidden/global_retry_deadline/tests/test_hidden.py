import unittest
from retrying import Clock, run

class Hidden(unittest.TestCase):
    def test_deadline_is_not_renewed(self):
        attempts = [0]

        def work():
            attempts[0] += 1
            if attempts[0] < 3:
                raise TimeoutError()
            return "ok"

        self.assertEqual(run(work, Clock([0, 4, 5, 6, 7])), "timed_out")
        self.assertEqual(attempts[0], 2)
