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
        self.assertIn('external_adapter_cleanup_decision_retention_trim_17', source)
        self.assertIn('EXTERNAL_REGISTRY', source)
        self.assertNotIn('stale compatibility note cleanup_decision_retention_trim_17', source)
        self.assertTrue(Path('adapters/cleanup_decision_retention_trim_17.py').is_file())
        self.assertTrue(Path('runtime/cleanup_decision_retention_trim_17.json').is_file())
        self.assertNotIn('old contract cleanup_decision_retention_trim_17', Path('README.md').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
