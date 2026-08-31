import unittest
from policy import evaluate

CASES = (((False, 0.0, 0.01), 'migrate'),)

class PublicContract(unittest.TestCase):
    def test_contract(self):
        for arguments, expected in CASES:
            with self.subTest(arguments=arguments):
                self.assertEqual(evaluate(*arguments), expected)
