import unittest
from inventory import Reservation, Store

class Public(unittest.TestCase):
    def test_available_stock_is_reserved(self):
        class RejectingStore(Store):
            def compare_and_reserve(self, expected_version, amount):
                return False

        store = RejectingStore(3)
        reservation = Reservation(store)
        self.assertFalse(reservation.reserve(2))
        self.assertEqual(store.quantity, 3)
