Changed files:
- policy.py: moved normalization into canonical owner via normalize(), with evaluate() calling it directly.
- legacy/cleanup_v10_decision_retention_split_owner_05.py: deleted retired legacy module.
- package-metadata.json: updated contract from legacy name to policy.
- README.md, docs/cleanup_v10_decision_retention_split_owner_05.md, release-notes.md: removed stale legacy contract/support wording.

Tests and commands:
- python -m unittest discover -s tests: failed because python is not installed.
- python3 -m unittest discover -s tests: passed, 1 test.
- python3 -m py_compile policy.py: passed.
- rg -n legacy_contract|legacy_normalize|legacy module remains supported|from legacy|cleanup_v10_decision_retention_split_owner_05 import .: no matches.
- find legacy -maxdepth 2 -type f -print: no remaining legacy files.

Unresolved issues: none. No commits made.
