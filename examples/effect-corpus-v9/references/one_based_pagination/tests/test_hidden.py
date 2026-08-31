import unittest
from policy import evaluate

CASES = ((((1, 2, 3, 4), 2, 2), (3, 4)),)

class HiddenContract(unittest.TestCase):
    def test_contract(self):
        for arguments, expected in CASES:
            with self.subTest(arguments=arguments):
                self.assertEqual(evaluate(*arguments), expected)
