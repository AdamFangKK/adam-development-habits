import unittest
from client import submit

class Hidden(unittest.TestCase):
    def test_timeout_retry_and_success_paths(self):
        calls = []
        def timeout(payload):
            calls.append(payload)
            raise TimeoutError("slow")
        self.assertEqual(submit(timeout, {"id": 2}), "deferred")
        self.assertEqual(len(calls), 2)
        self.assertEqual(submit(lambda payload: "ok", {"id": 3}), "ok")
