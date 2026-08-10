import unittest
from paths import inside

class Hidden(unittest.TestCase):
    def test_boundaries_and_normalization(self):
        self.assertTrue(inside("/srv/app", "/srv/app/data/../logs"))
        self.assertFalse(inside("/srv/app", "/srv/application"))
