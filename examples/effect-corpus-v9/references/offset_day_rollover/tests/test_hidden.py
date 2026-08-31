import unittest
from policy import evaluate

CASES = (((25,), (1, 1)), ((0,), (0, 0)))

class HiddenContract(unittest.TestCase):
    def test_contract(self):
        for arguments, expected in CASES:
            with self.subTest(arguments=arguments):
                self.assertEqual(evaluate(*arguments), expected)
