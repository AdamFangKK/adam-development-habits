import unittest
from policy import evaluate

CASES = (((2, 3, True, True), True), ((1, 3, False, True), False), ((1, 3, True, False), False))

class HiddenContract(unittest.TestCase):
    def test_contract(self):
        for arguments, expected in CASES:
            with self.subTest(arguments=arguments):
                self.assertEqual(evaluate(*arguments), expected)
