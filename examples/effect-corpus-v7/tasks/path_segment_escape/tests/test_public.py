import unittest
from paths import inside

class Public(unittest.TestCase):
    def test_sibling_prefix_is_outside(self):
        self.assertFalse(inside("/srv/app", "/srv/app2/data"))
