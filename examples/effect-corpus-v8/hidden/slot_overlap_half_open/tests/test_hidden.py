import unittest
from scheduler import can_add

class Hidden(unittest.TestCase):
    def test_real_overlap_is_still_rejected(self):
        self.assertFalse(can_add([(10, 12)], (11, 13)))
        self.assertTrue(can_add([(10, 12), (14, 15)], (12, 14)))
