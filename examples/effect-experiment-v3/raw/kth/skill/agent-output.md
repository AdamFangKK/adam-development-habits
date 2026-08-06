Implemented the minimal fix in [buggy.py](/tmp/adam-effect-kth-skill-lw4w3n68/buggy.py:12): upper-partition recursion now adjusts `k` by the number of elements at or below the pivot.

Evidence ledger:
- Baseline: public tests failed with recursive `IndexError`.
- Verification: `python3 test_public.py` passed, `2 public cases passed`.
- Changed files: `buggy.py` only.
- Remaining risk: hidden cases were not inspected, per instruction.