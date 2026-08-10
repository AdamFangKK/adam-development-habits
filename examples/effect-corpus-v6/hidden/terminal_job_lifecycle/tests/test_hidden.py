import unittest
from jobs import Job, TerminalError

class Hidden(unittest.TestCase):
    def test_terminal_rejection_is_durable(self):
        job = Job(lambda: (_ for _ in ()).throw(TerminalError()))
        self.assertEqual(job.process(), "failed")
        self.assertEqual(job.process(), "ignored")
        self.assertEqual(job.attempts, 1)
