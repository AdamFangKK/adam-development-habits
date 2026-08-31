import importlib
import json
from pathlib import Path
import unittest

from policy import evaluate

class HiddenContract(unittest.TestCase):
    def test_hidden_behavior(self):
        self.assertEqual(evaluate(' User '), 'user')

    def test_complete_retirement_or_retention(self):
        self.assertNotIn('legacy_contract_cleanup_v10_decision_retention_semantic_duplicate_19', Path('policy.py').read_text(encoding='utf-8'))
        self.assertNotIn('legacy_contract_cleanup_v10_decision_retention_semantic_duplicate_19', Path('README.md').read_text(encoding='utf-8'))
        self.assertNotIn('legacy_contract_cleanup_v10_decision_retention_semantic_duplicate_19', Path('docs/cleanup_v10_decision_retention_semantic_duplicate_19.md').read_text(encoding='utf-8'))
        self.assertNotIn('legacy_contract_cleanup_v10_decision_retention_semantic_duplicate_19', Path('release-notes.md').read_text(encoding='utf-8'))
        self.assertFalse(Path('helpers/cleanup_v10_decision_retention_semantic_duplicate_19_alias.py').exists())
        self.assertFalse(Path('compat/legacy_wrapper.py').exists())
        self.assertNotIn('normalize_alias', Path('policy.py').read_text(encoding='utf-8'))
        self.assertIn('owner: policy.canonical_normalize', Path('policy.py').read_text(encoding='utf-8'))
