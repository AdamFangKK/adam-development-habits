Changed files:
- policy.py: replaced stale legacy docstring/comment with implementation-local owner contract for policy.canonical_normalize; behavior unchanged.
- README.md, VERSION.md, CHANGELOG.md, runbook.md, docs/cleanup_v10_decision_retention_release_drift_04.md: synchronized the current contract.

Verification:
- python3 -m unittest tests/test_public.py: passed, 1 test.
- python3 -m py_compile policy.py: passed.
- rg -n legacy_contract_cleanup_v10_decision_retention_release_drift_04: zero matches.
- rg --files -g '!.*': only expected visible workspace files; no cache/debug leftovers observed.

Unresolved issues: none. No commits made.
