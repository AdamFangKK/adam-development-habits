import unittest
from datetime import date
from calendar_key import week_key

class Public(unittest.TestCase):
    def test_january_day_can_belong_to_previous_iso_year(self):
        self.assertEqual(week_key(date(2021, 1, 1)), "2020-W53")
