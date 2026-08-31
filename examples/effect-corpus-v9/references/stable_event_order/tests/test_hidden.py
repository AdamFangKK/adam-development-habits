import unittest
from policy import evaluate

CASES = (((((1, 'a'), (1, 'b')),), ('a', 'b')),)

class HiddenContract(unittest.TestCase):
    def test_contract(self):
        for arguments, expected in CASES:
            with self.subTest(arguments=arguments):
                self.assertEqual(evaluate(*arguments), expected)
