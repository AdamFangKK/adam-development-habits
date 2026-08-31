import unittest
from policy import evaluate

CASES = ((('tenant-b', 'u1', 'doc'), ('tenant-b', 'u1', 'doc')),)

class HiddenContract(unittest.TestCase):
    def test_contract(self):
        for arguments, expected in CASES:
            with self.subTest(arguments=arguments):
                self.assertEqual(evaluate(*arguments), expected)
