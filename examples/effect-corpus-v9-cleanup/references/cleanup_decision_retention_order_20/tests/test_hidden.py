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
        self.assertIn('external_adapter_cleanup_decision_retention_order_20', source)
        self.assertIn('EXTERNAL_REGISTRY', source)
        self.assertNotIn('stale compatibility note cleanup_decision_retention_order_20', source)


if __name__ == '__main__':
    unittest.main()
