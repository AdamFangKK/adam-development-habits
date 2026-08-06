Fixed `bitcount` in [buggy.py](/private/tmp/adam-effect-bitcount-baseline-5ua9f4bw/buggy.py) by clearing the lowest set bit with `n &= n - 1`.

Verified: `python3 test_public.py` → `3 public cases passed`.