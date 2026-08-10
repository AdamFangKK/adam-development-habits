import unittest
from handler import accept
from signer import signature

class Hidden(unittest.TestCase):
    def test_compact_body_and_wrong_signature(self):
        raw = '{"a":1,"b":2}'
        self.assertTrue(accept(raw, signature(raw)))
        self.assertFalse(accept(raw, signature('{"b":2,"a":1}')))
