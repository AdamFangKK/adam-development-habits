Fixed `bitcount` in [buggy.py](/tmp/adam-effect-bitcount-baseline-ad99tsx5/buggy.py) by clearing the lowest set bit with `n &= n - 1`.

Verified: `python3 test_public.py` passed all 3 public cases.