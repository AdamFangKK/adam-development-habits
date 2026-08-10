import unittest
from cache import Cache
from service import remove

class Hidden(unittest.TestCase):
    def test_other_entities_and_tenants_survive(self):
        cache = Cache()
        cache.put("a", "profile", "A")
        cache.put("a", "settings", "S")
        cache.put("b", "profile", "B")
        remove(cache, "a", "profile")
        self.assertEqual(cache.get("a", "settings"), "S")
        self.assertEqual(cache.get("b", "profile"), "B")
