import unittest
from identity import same

class Hidden(unittest.TestCase):
    def test_casefolding_and_non_match(self):
        self.assertTrue(same("WEIß", "weiss"))
        self.assertFalse(same("alpha", "alphabet"))
