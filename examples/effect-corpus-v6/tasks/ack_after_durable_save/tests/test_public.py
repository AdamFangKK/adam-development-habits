import unittest
from inbox import Inbox, Store
from worker import Worker

class Public(unittest.TestCase):
    def test_success_is_saved_and_acked(self):
        inbox, store = Inbox(), Store(fail=True)
        with self.assertRaises(OSError):
            Worker(inbox, store).handle({"id": "j1"})
        self.assertEqual(inbox.acknowledged, [])
