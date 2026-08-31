import unittest
from policy import evaluate

CASES = (((True, False), 1), ((True, True), 2))

class HiddenContract(unittest.TestCase):
    def test_contract(self):
        for arguments, expected in CASES:
            with self.subTest(arguments=arguments):
                self.assertEqual(evaluate(*arguments), expected)
