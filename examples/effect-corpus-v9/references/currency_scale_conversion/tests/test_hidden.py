import unittest
from policy import evaluate

CASES = (((1234, 2), 12.34), ((5, 0), 5.0))

class HiddenContract(unittest.TestCase):
    def test_contract(self):
        for arguments, expected in CASES:
            with self.subTest(arguments=arguments):
                self.assertEqual(evaluate(*arguments), expected)
