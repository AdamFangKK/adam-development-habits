import unittest
from dedup import unique

class Hidden(unittest.TestCase):
    def test_order_and_unhashable_rejection_are_stable(self):
        self.assertEqual(unique([3, 1, 3, 2, 1]), [3, 1, 2])
        with self.assertRaises(TypeError):
            unique([[1], [1]])
