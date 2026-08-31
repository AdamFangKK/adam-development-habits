from pathlib import Path
import unittest

from policy import evaluate

CASES = ((('\nvalue\t',), 'value'),)

class HiddenContract(unittest.TestCase):
    def test_current_behavior(self):
        for arguments, expected in CASES:
            with self.subTest(arguments=arguments):
                self.assertEqual(evaluate(*arguments), expected)

    def test_retirement_hygiene(self):
        source = Path('policy.py').read_text(encoding='utf-8')
        self.assertNotIn('old contract cleanup_decision_retention_trim_12', source)
        self.assertIn('Current contract cleanup_decision_retention_trim_12', source)


if __name__ == '__main__':
    unittest.main()
