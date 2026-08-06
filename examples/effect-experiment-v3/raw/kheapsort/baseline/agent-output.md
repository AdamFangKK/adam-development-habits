Fixed `kheapsort` in [buggy.py](/tmp/adam-effect-kheapsort-baseline-xojy8nr9/buggy.py) by using a `k + 1` heap window and processing only the remaining elements.

Verification: `python3 test_public.py` passed all 2 public cases.