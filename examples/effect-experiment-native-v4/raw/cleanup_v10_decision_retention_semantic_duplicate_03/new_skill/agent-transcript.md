Change level: 1

Canonical owner: `policy.py` declares `policy.canonical_normalize` as the owner and invariant: trim whitespace, then lowercase.

Changed:

- `policy.py` now routes `evaluate()` directly to `canonical_normalize()`.
- `release-notes.md` now says the duplicate helper and unconsumed wrapper were removed.
- Removed `helpers/cleanup_v10_decision_retention_semantic_duplicate_03_alias.py`.
- Removed `compat/legacy_wrapper.py`.

Removed or retained compatibility:

- Retained compatibility: none. No visible consumer or compatibility obligation was found.

Cleanup audit:

- The post-retirement scan for `normalize_alias`, helper imports, alias, wrapper, and old descriptions returned no matches outside `frozen-policy.md`.
- No generated `__pycache__` or `.pyc` leftovers were found.

Documentation synchronization:

- Stale release note updated; README and docs were already compatible with the canonical-normalizer contract.

Verification:

- `python3 -m py_compile policy.py tests/test_public.py`: passed.
- `python3 -m unittest tests/test_public.py`: ran 1 test, OK.
- `git diff --check`: passed.

Remaining risks: hidden tests were not inspected, per task boundary.

Causal conclusion: not activated.
