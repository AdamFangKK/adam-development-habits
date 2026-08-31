import unittest
from policy import evaluate

CASES = (((503,), True), ((401,), False), ((429,), True))

class HiddenContract(unittest.TestCase):
    def test_contract(self):
        for arguments, expected in CASES:
            with self.subTest(arguments=arguments):
                self.assertEqual(evaluate(*arguments), expected)
