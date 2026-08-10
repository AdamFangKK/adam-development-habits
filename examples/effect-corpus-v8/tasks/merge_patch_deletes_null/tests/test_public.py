import unittest
from merge_patch import apply_patch

class Public(unittest.TestCase):
    def test_null_removes_existing_key(self):
        self.assertEqual(apply_patch({"name": "a", "tag": "old"}, {"tag": None}), {"name": "a"})
