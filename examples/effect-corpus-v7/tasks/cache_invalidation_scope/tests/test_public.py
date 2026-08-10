import unittest
from cache import Cache
from service import remove

class Public(unittest.TestCase):
    def test_invalidation_is_tenant_scoped(self):
        cache = Cache()
        cache.put("a", "profile", "A")
        cache.put("b", "profile", "B")
        self.assertIsNone(remove(cache, "a", "profile"))
        self.assertEqual(cache.get("b", "profile"), "B")
