import unittest
from merge_patch import apply_patch

class Hidden(unittest.TestCase):
    def test_delete_missing_and_update_existing_keys(self):
        self.assertEqual(apply_patch({"a": 1}, {"missing": None}), {"a": 1})
        self.assertEqual(apply_patch({"a": 1}, {"a": 2, "b": 3}), {"a": 2, "b": 3})
