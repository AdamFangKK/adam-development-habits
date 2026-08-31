from pathlib import Path
import unittest

from policy import evaluate

CASES = (((5, 0), 5.0),)

class HiddenContract(unittest.TestCase):
    def test_current_behavior(self):
        for arguments, expected in CASES:
            with self.subTest(arguments=arguments):
                self.assertEqual(evaluate(*arguments), expected)

    def test_retirement_hygiene(self):
        source = Path('policy.py').read_text(encoding='utf-8')
        self.assertNotIn('legacy_cleanup_repair_scale_34', source)
        self.assertNotIn('Legacy path retained', source)


if __name__ == '__main__':
    unittest.main()
