import unittest
from policy import evaluate

CASES = ((((1, 2, 3, 4), 1, 2), (1, 2)),)

class PublicContract(unittest.TestCase):
    def test_contract(self):
        for arguments, expected in CASES:
            with self.subTest(arguments=arguments):
                self.assertEqual(evaluate(*arguments), expected)
