import unittest
from policy import evaluate

CASES = (((0.0, 0.01, 45, 30), 'stop'),)

class PublicContract(unittest.TestCase):
    def test_contract(self):
        for arguments, expected in CASES:
            with self.subTest(arguments=arguments):
                self.assertEqual(evaluate(*arguments), expected)
