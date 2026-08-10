import unittest
from ttl_cache import Cache

class Public(unittest.TestCase):
    def test_immediate_read(self):
        cache = Cache()
        cache.put("k", "v", 1000, 10)
        self.assertIsNone(cache.get("k", 11.1))
