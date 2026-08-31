from pathlib import Path
import unittest

from policy import evaluate

CASES = (((' User@example.com ',), 'user@example.com'),)

class HiddenContract(unittest.TestCase):
    def test_current_behavior(self):
        for arguments, expected in CASES:
            with self.subTest(arguments=arguments):
                self.assertEqual(evaluate(*arguments), expected)

    def test_retirement_hygiene(self):
        source = Path('policy.py').read_text(encoding='utf-8')
        self.assertNotIn('old contract cleanup_decision_retention_casefold_06', source)
        self.assertIn('Current contract cleanup_decision_retention_casefold_06', source)
        self.assertNotIn('old contract cleanup_decision_retention_casefold_06', Path('README.md').read_text(encoding='utf-8'))
        self.assertIn('Current contract cleanup_decision_retention_casefold_06', Path('docs/cleanup_decision_retention_casefold_06.md').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
