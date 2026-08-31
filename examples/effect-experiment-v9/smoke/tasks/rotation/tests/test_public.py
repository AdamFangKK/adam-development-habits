import unittest

from policy import evaluate


class RotationContract(unittest.TestCase):
    def test_distance_wraps(self):
        self.assertEqual(evaluate((1, 2, 3), 4), (2, 3, 1))


if __name__ == "__main__":
    unittest.main()
