import unittest
from orders import create_order
from profile import Profile

class Hidden(unittest.TestCase):
    def test_later_profile_mutations_do_not_rewrite_order(self):
        profile = Profile({"city": "Old", "street": "1 Main"})
        order = create_order(profile)
        profile.address["street"] = "2 Main"
        self.assertEqual(order["ship_to"], {"city": "Old", "street": "1 Main"})
