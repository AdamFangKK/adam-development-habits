import unittest
from events import parse

class Hidden(unittest.TestCase):
    def test_missing_version_is_legacy(self):
        self.assertEqual(parse({"name": "Grace"}), {"name": "Grace"})
