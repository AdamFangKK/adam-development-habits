import unittest
from flags import enabled

class Hidden(unittest.TestCase):
    def test_tenant_is_part_of_rollout_identity(self):
        self.assertNotEqual(enabled("acme", "u1"), enabled("globex", "u1"))
