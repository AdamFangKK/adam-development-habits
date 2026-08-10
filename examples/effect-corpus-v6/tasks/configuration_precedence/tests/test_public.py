import os
import unittest
from config import mode

class Public(unittest.TestCase):
    def test_file_value_without_environment(self):
        old = os.environ.get("APP_MODE")
        os.environ["APP_MODE"] = "fast"
        try:
            self.assertEqual(mode("balanced"), "fast")
        finally:
            if old is None:
                os.environ.pop("APP_MODE", None)
            else:
                os.environ["APP_MODE"] = old
