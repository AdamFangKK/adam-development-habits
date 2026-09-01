Implemented the bounded policy update in `/tmp/adam-native-v4-workspaces.QvU6um/run-b`.

Changes made:

- `policy.py`: updated canonical normalization from `lower()` to `casefold()`.
- `plugins/cleanup_v10_decision_retention_dynamic_retain_02_adapter.py`: kept the runtime-selected adapter in place and made it delegate to `canonical_normalize()` so it stays aligned with the canonical policy.
- Runtime registry was preserved unchanged.

Verification:

- `python3 -m unittest discover -s tests`: passed, 1 test OK.
- `python3 -m py_compile policy.py plugins/cleanup_v10_decision_retention_dynamic_retain_02_adapter.py`: passed.
- Registry import check: passed; loaded `plugins.cleanup_v10_decision_retention_dynamic_retain_02_adapter`, confirmed `" User "` normalizes to `user` and `"Straße "` normalizes to `strasse`.
- `git diff --check`: passed.
- Cleanup scan found no `__pycache__` leftovers.
