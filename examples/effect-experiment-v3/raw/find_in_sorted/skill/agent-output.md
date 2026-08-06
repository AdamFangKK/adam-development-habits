Implemented the minimal fix in [buggy.py](/tmp/adam-effect-find_in_sorted-skill-l4thampy/buggy.py).

Evidence ledger:
- Canonical owner: `find_in_sorted`
- Invariant: search bounds strictly shrink; return matching index or `-1`
- Change: advance to `mid + 1` and handle exhausted intervals
- Removed paths: none
- Verification: `python3 test_public.py` → `2 public cases passed`
- Remaining risk: hidden-case coverage not inspected, per instructions

Only `buggy.py` was modified; no commit was created.