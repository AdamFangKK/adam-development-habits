import unittest
from inbox import Inbox, Store
from worker import Worker

class Hidden(unittest.TestCase):
    def test_failed_save_is_not_acked(self):
        inbox, store = Inbox(), Store(fail=True)
        with self.assertRaises(OSError):
            Worker(inbox, store).handle({"id": "j2"})
        self.assertEqual(inbox.acknowledged, [])
