import unittest
from policy import evaluate

CASES = ((('tenant-b', 'profile'), ('tenant-b', 'profile')),)

class HiddenContract(unittest.TestCase):
    def test_contract(self):
        for arguments, expected in CASES:
            with self.subTest(arguments=arguments):
                self.assertEqual(evaluate(*arguments), expected)
