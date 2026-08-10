import unittest
from notifier import Notifier

class Hidden(unittest.TestCase):
    def test_duplicate_is_channel_specific(self):
        notifier = Notifier()
        self.assertTrue(notifier.send("email", "e1", "hello"))
        self.assertFalse(notifier.send("email", "e1", "hello again"))
        self.assertTrue(notifier.send("push", "e1", "hello"))
