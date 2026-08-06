Implemented the binary-search repair in [buggy.py](/tmp/adam-effect-find_first_in_sorted-skill-8hmwcf_n/buggy.py).

Evidence ledger:
- Canonical owner: `find_first_in_sorted`
- Invariant: lower-bound search over `[lo, hi)`
- Scope: only `buggy.py`; no dependencies or compatibility changes
- Verification: `python3 test_public.py` passed 2 cases; 7 boundary cases passed
- Remaining risk: none identified for the documented sorted-list contract