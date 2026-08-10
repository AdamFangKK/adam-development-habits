import unittest
from records import Records

class Hidden(unittest.TestCase):
    def test_other_tenant_cannot_update(self):
        with self.assertRaises(PermissionError):
            Records().update("globex", "r1", "stolen")
