import unittest
from policy import evaluate

CASES = ((('Straße@EXAMPLE.COM',), 'strasse@example.com'),)

class HiddenContract(unittest.TestCase):
    def test_contract(self):
        for arguments, expected in CASES:
            with self.subTest(arguments=arguments):
                self.assertEqual(evaluate(*arguments), expected)
