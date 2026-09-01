Changed files:
- policy.py: replaced stale legacy docstring with canonical policy wording.
- plugins/cleanup_v10_decision_retention_dynamic_retain_06_adapter.py: retained the runtime-selected adapter and delegated to policy.canonical_normalize.
- README.md, docs/cleanup_v10_decision_retention_dynamic_retain_06.md, runbook.md: removed stale legacy contract wording and synchronized documentation.

Verification:
- python3 -m unittest tests/test_public.py: passed, 1 test.
- python3 -m unittest discover -s tests: passed, 1 test.
- python3 -m py_compile policy.py plugins/cleanup_v10_decision_retention_dynamic_retain_06_adapter.py: passed.
- rg stale-marker scan across README, docs, runbook, policy, plugins, and runtime: no matches.

Unresolved issues: none. No commits made.
