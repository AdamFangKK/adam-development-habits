import unittest
from row_parser import parse_row

class Hidden(unittest.TestCase):
    def test_trailing_and_whitespace_blanks_are_preserved(self):
        self.assertEqual(parse_row(" x , ,z,"), ["x", "", "z", ""])
        self.assertEqual(parse_row(""), [""])
