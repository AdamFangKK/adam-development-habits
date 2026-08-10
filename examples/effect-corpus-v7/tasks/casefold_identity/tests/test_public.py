import unittest
from identity import same

class Public(unittest.TestCase):
    def test_unicode_casefolding(self):
        self.assertTrue(same("Straße", "STRASSE"))
