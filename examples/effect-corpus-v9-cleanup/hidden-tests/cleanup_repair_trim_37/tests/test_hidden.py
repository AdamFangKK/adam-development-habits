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
        self.assertNotIn('legacy_cleanup_repair_trim_37', source)
        self.assertNotIn('Legacy path retained', source)
        self.assertFalse(Path('legacy/cleanup_repair_trim_37.py').exists())
        self.assertFalse(Path('config/cleanup_repair_trim_37.toml').exists())
        self.assertNotIn('old contract cleanup_repair_trim_37', Path('README.md').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
