import unittest
from jobs import Job, TerminalError

class Public(unittest.TestCase):
    def test_success(self):
        self.assertEqual(Job(lambda: (_ for _ in ()).throw(TerminalError())).process(), "failed")
