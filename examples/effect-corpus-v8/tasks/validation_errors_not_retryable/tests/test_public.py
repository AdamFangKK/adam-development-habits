import unittest
from client import submit

class Public(unittest.TestCase):
    def test_validation_error_is_not_retried(self):
        calls = []
        def send(payload):
            calls.append(payload)
            raise ValueError("bad payload")
        with self.assertRaises(ValueError):
            submit(send, {"id": 1})
        self.assertEqual(calls, [{"id": 1}])
