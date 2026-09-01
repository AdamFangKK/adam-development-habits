Changed files:
- policy.py: moved normalization into canonical owner policy.evaluate with implementation-local ownership/invariant docstring.
- README.md, docs/policy.md, release-notes.md, package-metadata.json: synchronized contract text to policy.evaluate.
- legacy/cleanup_v10_decision_retention_split_owner_05.py and docs/cleanup_v10_decision_retention_split_owner_05.md: removed retired implementation and old documentation surface.
- legacy/: removed after becoming empty.

Verification:
- python3 -m unittest tests/test_public.py: passed, 1 test.
- python3 -m py_compile policy.py: passed.
- python3 -m json.tool package-metadata.json: passed.
- Retired path absence checks: passed.
- Stale-marker scan excluding task.md, frozen-policy.md, tests, and caches: zero matches.

Unresolved issues: none. No commits made.
