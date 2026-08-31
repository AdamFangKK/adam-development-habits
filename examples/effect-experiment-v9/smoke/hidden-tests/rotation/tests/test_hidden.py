import unittest

from policy import evaluate


class RotationHiddenContract(unittest.TestCase):
    def test_empty_and_negative_distance(self):
        self.assertEqual(evaluate((), 8), ())
        self.assertEqual(evaluate((1, 2, 3), -1), (3, 1, 2))


if __name__ == "__main__":
    unittest.main()
