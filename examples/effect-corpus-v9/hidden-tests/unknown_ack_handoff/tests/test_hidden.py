import unittest
from policy import evaluate

CASES = ((('FOUND', False), True), (('UNKNOWN', True), True), (('UNKNOWN', False), False))

class HiddenContract(unittest.TestCase):
    def test_contract(self):
        for arguments, expected in CASES:
            with self.subTest(arguments=arguments):
                self.assertEqual(evaluate(*arguments), expected)
