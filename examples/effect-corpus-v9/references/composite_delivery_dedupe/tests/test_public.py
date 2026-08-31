import unittest
from policy import evaluate

CASES = ((('tenant-a', 'evt-1'), ('tenant-a', 'evt-1')),)

class PublicContract(unittest.TestCase):
    def test_contract(self):
        for arguments, expected in CASES:
            with self.subTest(arguments=arguments):
                self.assertEqual(evaluate(*arguments), expected)
