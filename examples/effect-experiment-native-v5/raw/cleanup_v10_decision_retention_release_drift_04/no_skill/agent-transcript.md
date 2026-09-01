Changed files:
- VERSION.md: expanded support/version note for retained canonical normalization behavior.
- README.md: aligned overview with evaluate(value) and linked release/recovery docs.
- docs/cleanup_v10_decision_retention_release_drift_04.md: clarified retained policy contract.
- runbook.md: added recovery objective and checks.
- CHANGELOG.md: added current release entry noting no behavior change.
- policy.py: not modified.

Tests and commands:
- python -m unittest tests/test_public.py: failed because python is unavailable.
- python -m py_compile policy.py: failed because python is unavailable.
- python3 -m unittest tests/test_public.py: passed, 1 test.
- python3 -m py_compile policy.py: passed.
- find for __pycache__: no generated leftovers.

Unresolved issues: none. No commits made.
