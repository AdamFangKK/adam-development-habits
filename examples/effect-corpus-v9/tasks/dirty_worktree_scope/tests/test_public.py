import unittest
from policy import evaluate

CASES = (((('owner.py', 'notes.txt'), ('owner.py',)), ('owner.py',)),)

class PublicContract(unittest.TestCase):
    def test_contract(self):
        for arguments, expected in CASES:
            with self.subTest(arguments=arguments):
                self.assertEqual(evaluate(*arguments), expected)
