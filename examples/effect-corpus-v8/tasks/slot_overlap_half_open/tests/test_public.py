import unittest
from scheduler import can_add

class Public(unittest.TestCase):
    def test_adjacent_slots_do_not_overlap(self):
        self.assertTrue(can_add([(10, 11)], (11, 12)))
