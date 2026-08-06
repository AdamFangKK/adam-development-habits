Implemented the minimal `lcs_length` repair in [buggy.py](/tmp/adam-effect-lcs_length-skill-ntp_4973/buggy.py).

Evidence ledger:
- Canonical owner: `buggy.py:lcs_length`
- Invariant: contiguous matches extend diagonally; mismatches reset.
- Change: rolling DP row; removed incorrect `Counter` logic.
- Verification: baseline failed (`actual=1`); `python3 test_public.py` passes all 3 cases within timeout.
- Changed files: `buggy.py` only
- Commit: none 
