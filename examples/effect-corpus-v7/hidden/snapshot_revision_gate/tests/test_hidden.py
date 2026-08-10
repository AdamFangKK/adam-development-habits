import unittest
from state import Store
from view import refresh

class Hidden(unittest.TestCase):
    def test_duplicate_and_stale_revisions_do_not_replace_state(self):
        store = Store()
        refresh(store, 4, {"count": 4})
        self.assertEqual(refresh(store, 4, {"count": 44}), (4, {"count": 4}))
        self.assertEqual(refresh(store, 3, {"count": 3}), (4, {"count": 4}))
