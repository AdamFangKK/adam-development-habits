Implemented `lcs_length` in [buggy.py](/private/tmp/adam-effect-lcs_length-skill-dq7jdwtx/buggy.py:1) using one-dimensional dynamic programming for longest common substring semantics.

Evidence ledger:
- Level: 1
- Baseline: public test failed (`actual=1`, expected `2`)
- Verification: `python3 test_public.py` passed all 3 cases
- Scope: only `buggy.py` modified
- `git diff --check`: passed
- Remaining risk: hidden cases were not inspected, per instruction