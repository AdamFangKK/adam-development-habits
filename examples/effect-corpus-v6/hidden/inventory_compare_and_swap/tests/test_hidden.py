import unittest
from inventory import Reservation, Store

class Hidden(unittest.TestCase):
    def test_stale_version_is_not_reported_as_success(self):
        class StaleReadStore(Store):
            def read(self):
                quantity, _ = super().read()
                return quantity, 1

        store = StaleReadStore(3)
        store.version = 2
        reservation = Reservation(store)
        self.assertFalse(reservation.reserve(2))
        self.assertEqual(store.quantity, 3)
