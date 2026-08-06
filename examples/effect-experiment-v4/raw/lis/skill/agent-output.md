Implemented the minimal fix in [buggy.py](/tmp/adam-effect-lis-skill-3fhpb942/buggy.py:14): `longest` now never decreases when a shorter LIS tail is replaced.

Evidence ledger:

- Change level: 1
- Cause: tail replacement incorrectly reset the tracked maximum length.
- Invariant: `longest` is monotonic.
- Verification: `python3 test_public.py` passed all 4 cases with the supplied one-second timeout.
- Additional check: exhaustive unique permutations through length 7 passed.
- Scope: only `buggy.py` modified; no commit made.
- Remaining risk: existing algorithm remains `O(n²)` for very large inputs.