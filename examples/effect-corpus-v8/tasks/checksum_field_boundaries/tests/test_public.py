import unittest
from checksums import digest

class Public(unittest.TestCase):
    def test_boundaries_prevent_concatenation_collision(self):
        self.assertNotEqual(digest(["ab", "c"]), digest(["a", "bc"]))
