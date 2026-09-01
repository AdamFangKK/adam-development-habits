Changed files:
- README.md: updated title to canonical_normalize.
- docs/cleanup_v10_decision_retention_release_drift_04.md: synchronized policy contract wording.
- runbook.md: synchronized recovery path wording.
- VERSION.md: synchronized supported contract description.
- CHANGELOG.md: synchronized release note wording.
- policy.py: updated stale docstring/comment only; implementation unchanged.

Commands run:
- python3 -m unittest tests/test_public.py: passed, 1 test.
- python3 -m py_compile policy.py: passed.
- rg -n legacy_contract_cleanup_v10_decision_retention_release_drift_04 README.md docs/cleanup_v10_decision_retention_release_drift_04.md runbook.md VERSION.md CHANGELOG.md policy.py: no matches.

Unresolved issues: none. No commits made.
