import unittest
from accounts import account_key

class Public(unittest.TestCase):
    def test_local_part_case_is_preserved(self):
        self.assertEqual(account_key("Sales@EXAMPLE.COM"), "Sales@example.com")
