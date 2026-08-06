Implemented the LCS repair in [buggy.py](/private/tmp/adam-effect-longest_common_subsequence-skill-23l057ea/buggy.py) using bottom-up dynamic programming and deterministic reconstruction.

Evidence ledger:
- Change level: 1
- Invariant: result is a longest subsequence of both inputs.
- Verification: `python3 test_public.py` passed all 3 cases; syntax/invariant checks and `git diff --check` passed.
- Scope: only `buggy.py` modified; no dependencies or tests changed.
- Remaining risk: O(len(a) × len(b)) time and space.