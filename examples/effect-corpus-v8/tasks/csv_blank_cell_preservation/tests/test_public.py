import unittest
from row_parser import parse_row

class Public(unittest.TestCase):
    def test_empty_middle_cell_is_preserved(self):
        self.assertEqual(parse_row("a,,c"), ["a", "", "c"])
