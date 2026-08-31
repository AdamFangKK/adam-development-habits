import unittest
from policy import evaluate

CASES = (((True, True, True, True), True), ((True, False, True, True), False))

class HiddenContract(unittest.TestCase):
    def test_contract(self):
        for arguments, expected in CASES:
            with self.subTest(arguments=arguments):
                self.assertEqual(evaluate(*arguments), expected)
