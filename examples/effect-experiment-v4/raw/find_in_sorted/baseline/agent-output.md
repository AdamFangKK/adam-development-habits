Fixed `find_in_sorted` by handling single-element search intervals correctly, preventing infinite recursion.

Verification: `python3 test_public.py` passed all 2 public cases.