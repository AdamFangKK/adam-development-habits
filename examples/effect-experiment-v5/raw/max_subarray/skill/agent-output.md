Implemented the non-empty Kadane fix in [buggy.py](/tmp/adam-effect-max_subarray-skill-ea6f2cuh/buggy.py).

Evidence ledger:
- Complexity: O(n) time, O(1) extra space.
- Public verification: `python3 test_public.py` passed, 2 cases.
- Stress verification: 400,001-element case passed.
- Only `buggy.py` was modified; no tests, metadata, or commits changed.
- Remaining boundary: empty input has no valid non-empty subarray and raises `StopIteration`.