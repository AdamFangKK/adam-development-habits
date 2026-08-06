Implemented the `lis` repair in [buggy.py](/tmp/adam-effect-lis-skill-6wttek62/buggy.py:2) using an `O(n log n)` tails algorithm.

Evidence ledger:

- Change level: 1
- Canonical owner: `buggy.py::lis`
- Invariant: returns the length of the longest increasing subsequence.
- Changed files: `buggy.py` only
- Verification:
  - `python3 test_public.py`: `4 public cases passed`
  - Exhaustive unique-input oracle check: passed
  - 100,000-element performance smoke test: passed
  - In-memory compilation: passed
- Remaining risk: hidden tests were not inspected, per instructions.