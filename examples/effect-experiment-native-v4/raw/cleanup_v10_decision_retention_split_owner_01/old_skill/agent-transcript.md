Change level: 1

Canonical owner: `policy.normalize`

Changed:

- `policy.py` now owns normalization directly via `normalize(value)`; `evaluate()` delegates locally.
- `README.md`, `release-notes.md`, `package-metadata.json`, and `docs/policy-normalization.md` now describe `policy.normalize`.
- Deleted retired surfaces: `legacy/cleanup_v10_decision_retention_split_owner_01.py` and `docs/cleanup_v10_decision_retention_split_owner_01.md`.

Removed or retained compatibility:

- Removed the legacy module entirely.
- Retained compatibility: none. No live consumer found inside the visible workspace.

Cleanup audit:

- `rg -n "legacy_contract_cleanup_v10_decision_retention_split_owner_01|legacy_normalize|cleanup_v10_decision_retention_split_owner_01|legacy\\.cleanup|legacy module remains supported" .`: exit 1, no stale markers found.
- Final file sweep shows no `legacy/` files and no generated `.pytest_cache` or `__pycache__`.

Documentation synchronization:

- Updated README, release notes, package metadata, and canonical docs to the `policy.normalize` contract.

Verification:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider`: `1 passed in 0.00s`.
- Python import/smoke check for `normalize` and `evaluate`: exit 0.
- `git diff --check`: exit 0.
- `python3 -m json.tool package-metadata.json`: exit 0.

Remaining risks: none identified in the visible workspace.

Causal conclusion: not activated.
