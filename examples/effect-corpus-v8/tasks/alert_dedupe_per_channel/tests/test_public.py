import unittest
from notifier import Notifier

class Public(unittest.TestCase):
    def test_same_event_can_be_sent_on_two_channels(self):
        notifier = Notifier()
        self.assertTrue(notifier.send("email", "e1", "hello"))
        self.assertTrue(notifier.send("sms", "e1", "hello"))
        self.assertEqual(notifier.deliveries, [("email", "hello"), ("sms", "hello")])
