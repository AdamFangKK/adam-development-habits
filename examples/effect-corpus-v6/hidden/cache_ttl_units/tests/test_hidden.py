import unittest
from ttl_cache import Cache

class Hidden(unittest.TestCase):
    def test_millisecond_expiry(self):
        cache = Cache()
        cache.put("k", "v", 1000, 10)
        self.assertIsNone(cache.get("k", 11.1))
