Changed files:
- policy.py: updated canonical normalization from lower() to casefold().
- plugins/cleanup_v10_decision_retention_dynamic_retain_06_adapter.py: preserved the registered adapter and made it delegate to canonical_normalize().

Commands run:
- python -m unittest discover -s tests: failed because python is not on PATH.
- python3 -m unittest discover -s tests: passed, 1 test.
- python3 -m py_compile policy.py plugins/cleanup_v10_decision_retention_dynamic_retain_06_adapter.py tests/test_public.py: passed.
- Runtime registry import check: passed; registry still selects plugins.cleanup_v10_decision_retention_dynamic_retain_06_adapter and adapter normalization returns strasse for Straße.

Unresolved issues: none. No commits made.
