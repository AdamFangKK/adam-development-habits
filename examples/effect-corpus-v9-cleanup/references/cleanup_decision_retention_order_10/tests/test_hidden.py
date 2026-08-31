from pathlib import Path
import unittest

from policy import evaluate

CASES = (((((1, 'a'), (1, 'b')),), ('a', 'b')),)

class HiddenContract(unittest.TestCase):
    def test_current_behavior(self):
        for arguments, expected in CASES:
            with self.subTest(arguments=arguments):
                self.assertEqual(evaluate(*arguments), expected)

    def test_retirement_hygiene(self):
        source = Path('policy.py').read_text(encoding='utf-8')
        self.assertNotIn('new_duplicate_cleanup_decision_retention_order_10', source)
        self.assertFalse(Path('helpers/cleanup_decision_retention_order_10_duplicate.py').exists())
        self.assertNotIn('old contract cleanup_decision_retention_order_10', Path('README.md').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
