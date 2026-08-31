import unittest
from policy import evaluate

CASES = (((True,), ('disable_flag', 'revert_code')),)

class PublicContract(unittest.TestCase):
    def test_contract(self):
        for arguments, expected in CASES:
            with self.subTest(arguments=arguments):
                self.assertEqual(evaluate(*arguments), expected)
