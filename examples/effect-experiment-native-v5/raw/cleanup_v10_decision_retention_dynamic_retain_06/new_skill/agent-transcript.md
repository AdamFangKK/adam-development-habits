Changed files:
- policy.py: added implementation-local owner proof for policy.canonical_normalize and its invariant.
- plugins/cleanup_v10_decision_retention_dynamic_retain_06_adapter.py: retained the runtime-selected adapter, but changed it to delegate to policy.canonical_normalize.
- README.md, docs/cleanup_v10_decision_retention_dynamic_retain_06.md, runbook.md: synchronized docs to the canonical owner and retained-adapter contract.

Verification run:
- python3 -m unittest tests/test_public.py: passed, 1 test.
- Registry/import probe loading runtime/cleanup_v10_decision_retention_dynamic_retain_06.json adapter and calling normalize(' User '): returned user.
- python3 -m py_compile policy.py plugins/cleanup_v10_decision_retention_dynamic_retain_06_adapter.py: passed.
- rg -n legacy_contract README.md docs runbook.md policy.py plugins runtime: no matches.
- Search confirmed the remaining strip().lower() implementation is only in the canonical owner, with the adapter delegating to it.

Unresolved issues: none. No commits made.
