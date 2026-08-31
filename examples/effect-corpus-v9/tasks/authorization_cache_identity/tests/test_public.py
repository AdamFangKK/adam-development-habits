import unittest
from policy import evaluate

CASES = ((('tenant-a', 'u1', 'doc'), ('tenant-a', 'u1', 'doc')),)

class PublicContract(unittest.TestCase):
    def test_contract(self):
        for arguments, expected in CASES:
            with self.subTest(arguments=arguments):
                self.assertEqual(evaluate(*arguments), expected)
