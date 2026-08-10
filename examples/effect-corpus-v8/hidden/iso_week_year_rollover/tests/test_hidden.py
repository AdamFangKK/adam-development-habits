import unittest
from datetime import date
from calendar_key import week_key

class Hidden(unittest.TestCase):
    def test_iso_year_can_differ_in_both_directions(self):
        self.assertEqual(week_key(date(2018, 12, 31)), "2019-W01")
        self.assertEqual(week_key(date(2020, 6, 15)), "2020-W25")
