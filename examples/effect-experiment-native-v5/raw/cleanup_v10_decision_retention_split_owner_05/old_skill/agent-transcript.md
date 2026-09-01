Changed files:
- policy.py: moved normalization into canonical evaluate.
- legacy/cleanup_v10_decision_retention_split_owner_05.py: deleted retired legacy module.
- README.md, docs/cleanup_v10_decision_retention_split_owner_05.md, package-metadata.json, release-notes.md: updated stale legacy contract text to current owner.

Verification:
- rg -n legacy_normalize|legacy_contract_cleanup_v10_decision_retention_split_owner_05|legacy module remains supported|legacy module|from legacy --glob '!tests/**': no matches, exit 1.
- rg --files: legacy module no longer listed.
- python3 -m py_compile policy.py: exit 0.
- python3 -m json.tool package-metadata.json: exit 0.
- python3 -m unittest tests/test_public.py: ran 1 test, OK.
- find for __pycache__ and *.pyc: no generated leftovers.

Unresolved issues: none. No commits made.
