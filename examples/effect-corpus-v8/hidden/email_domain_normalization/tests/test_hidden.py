import unittest
from accounts import account_key

class Hidden(unittest.TestCase):
    def test_last_at_splits_address_and_domain_only_changes(self):
        self.assertEqual(account_key("A@B@Example.ORG"), "A@B@example.org")
