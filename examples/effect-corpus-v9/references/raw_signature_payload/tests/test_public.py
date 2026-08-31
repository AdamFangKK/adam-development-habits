import unittest
from policy import evaluate

CASES = (((b' {"x":1}\n',), b' {"x":1}\n'),)

class PublicContract(unittest.TestCase):
    def test_contract(self):
        for arguments, expected in CASES:
            with self.subTest(arguments=arguments):
                self.assertEqual(evaluate(*arguments), expected)
