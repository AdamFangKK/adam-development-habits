import unittest
from records import Records

class Public(unittest.TestCase):
    def test_owner_can_update(self):
        with self.assertRaises(PermissionError):
            Records().update("globex", "r1", "stolen")
