import unittest
from policy import evaluate

CASES = (((False, False), 'planned'), ((True, False), 'executed'), ((True, True), 'verified'))

class HiddenContract(unittest.TestCase):
    def test_contract(self):
        for arguments, expected in CASES:
            with self.subTest(arguments=arguments):
                self.assertEqual(evaluate(*arguments), expected)
