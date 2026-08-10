import unittest
from events import parse

class Public(unittest.TestCase):
    def test_current_event(self):
        self.assertEqual(parse({"version": 2, "payload": {"name": "Ada"}}), {"name": "Ada"})
        self.assertEqual(parse({"name": "Grace"}), {"name": "Grace"})
