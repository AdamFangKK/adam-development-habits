import importlib
import json
from pathlib import Path
import unittest

from policy import evaluate

class HiddenContract(unittest.TestCase):
    def test_hidden_behavior(self):
        self.assertEqual(evaluate(' User '), 'user')

    def test_complete_retirement_or_retention(self):
        self.assertNotIn('legacy_contract_cleanup_v10_decision_retention_split_owner_09', Path('policy.py').read_text(encoding='utf-8'))
        self.assertNotIn('legacy_contract_cleanup_v10_decision_retention_split_owner_09', Path('README.md').read_text(encoding='utf-8'))
        self.assertNotIn('legacy_contract_cleanup_v10_decision_retention_split_owner_09', Path('docs/cleanup_v10_decision_retention_split_owner_09.md').read_text(encoding='utf-8'))
        self.assertNotIn('legacy_contract_cleanup_v10_decision_retention_split_owner_09', Path('release-notes.md').read_text(encoding='utf-8'))
        self.assertNotIn('legacy_contract_cleanup_v10_decision_retention_split_owner_09', Path('package-metadata.json').read_text(encoding='utf-8'))
        self.assertFalse(Path('legacy/cleanup_v10_decision_retention_split_owner_09.py').exists())
        self.assertNotIn('legacy_normalize', Path('policy.py').read_text(encoding='utf-8'))
        self.assertIn('owner: policy.canonical_normalize', Path('policy.py').read_text(encoding='utf-8'))
