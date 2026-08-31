import unittest

from policy import evaluate

class PublicContract(unittest.TestCase):
    def test_visible_behavior(self):
        self.assertEqual(evaluate('User'), 'user')
