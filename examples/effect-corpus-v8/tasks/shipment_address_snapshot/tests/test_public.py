import unittest
from orders import create_order
from profile import Profile

class Public(unittest.TestCase):
    def test_order_keeps_checkout_address(self):
        profile = Profile({"city": "Old", "street": "1 Main"})
        order = create_order(profile)
        profile.update_city("New")
        self.assertEqual(order["ship_to"]["city"], "Old")
