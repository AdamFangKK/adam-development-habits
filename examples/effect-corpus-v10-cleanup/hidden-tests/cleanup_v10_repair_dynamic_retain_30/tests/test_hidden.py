import importlib
import json
from pathlib import Path
import unittest

from policy import evaluate

class HiddenContract(unittest.TestCase):
    def test_hidden_behavior(self):
        self.assertEqual(evaluate(' User '), 'user')

    def test_complete_retirement_or_retention(self):
        self.assertNotIn('legacy_contract_cleanup_v10_repair_dynamic_retain_30', Path('policy.py').read_text(encoding='utf-8'))
        self.assertNotIn('legacy_contract_cleanup_v10_repair_dynamic_retain_30', Path('README.md').read_text(encoding='utf-8'))
        self.assertNotIn('legacy_contract_cleanup_v10_repair_dynamic_retain_30', Path('docs/cleanup_v10_repair_dynamic_retain_30.md').read_text(encoding='utf-8'))
        self.assertNotIn('legacy_contract_cleanup_v10_repair_dynamic_retain_30', Path('runbook.md').read_text(encoding='utf-8'))
        registry = json.loads(Path('runtime/cleanup_v10_repair_dynamic_retain_30.json').read_text(encoding='utf-8'))
        self.assertEqual(registry['adapter'], 'plugins.cleanup_v10_repair_dynamic_retain_30_adapter')
        self.assertTrue(Path('plugins/cleanup_v10_repair_dynamic_retain_30_adapter.py').is_file())
        adapter = importlib.import_module(registry['adapter'])
        self.assertEqual(adapter.normalize(' User '), 'user')
        self.assertIn('owner: policy.canonical_normalize', Path('policy.py').read_text(encoding='utf-8'))
