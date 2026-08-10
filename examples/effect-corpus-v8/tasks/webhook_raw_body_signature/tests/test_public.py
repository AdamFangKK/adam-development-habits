import unittest
from handler import accept
from signer import signature

class Public(unittest.TestCase):
    def test_signature_uses_exact_raw_body(self):
        raw = '{"b":2, "a":1}'
        self.assertTrue(accept(raw, signature(raw)))
