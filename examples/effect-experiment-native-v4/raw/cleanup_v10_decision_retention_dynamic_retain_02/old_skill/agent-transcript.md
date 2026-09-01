Implemented the bounded policy update in `/tmp/adam-native-v4-workspaces.QvU6um/run-d`.

Changes made:

- `policy.py`: updated the canonical contract marker from legacy to canonical.
- `plugins/cleanup_v10_decision_retention_dynamic_retain_02_adapter.py`: preserved the runtime-selected adapter and changed it to delegate to `policy.canonical_normalize()`.
- `README.md`, `docs/cleanup_v10_decision_retention_dynamic_retain_02.md`, and `runbook.md`: synchronized stale legacy contract text to the canonical contract wording.
- Left `runtime/cleanup_v10_decision_retention_dynamic_retain_02.json` unchanged so the registry still selects the adapter.

Verification:

- `python3 -m py_compile policy.py plugins/cleanup_v10_decision_retention_dynamic_retain_02_adapter.py`: passed.
- `python3 -m unittest -v tests/test_public.py`: 1 test passed.
- `python3 -m unittest discover -s tests -p 'test*.py' -v`: 1 test passed.
- Registry behavior check: the runtime-selected adapter remained configured and `normalize(' User ')` returned `user`.
- Retirement sweep found no remaining legacy contract markers.
- No generated cache directories remained.
- `git diff --check`: passed.

Notes:

- The plugin adapter was retained because the runtime registry dynamically references it.
- The old legacy contract marker in canonical policy/docs/runbook was removed or updated.
