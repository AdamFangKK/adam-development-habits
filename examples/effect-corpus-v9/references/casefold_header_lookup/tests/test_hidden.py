import unittest
from policy import evaluate

CASES = ((({'X-ID': '7'}, 'x-id'), '7'), (({}, 'x'), None))

class HiddenContract(unittest.TestCase):
    def test_contract(self):
        for arguments, expected in CASES:
            with self.subTest(arguments=arguments):
                self.assertEqual(evaluate(*arguments), expected)
