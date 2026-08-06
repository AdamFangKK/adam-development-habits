Repaired [`buggy.py`](/tmp/adam-effect-bucketsort-skill-_imgn2ct/buggy.py:8) by iterating over `counts` when expanding sorted output.

Evidence ledger:
- Level: 1
- Acceptance: ascending output, empty input support, unchanged contract
- Verification: baseline failed; `python3 test_public.py` passed 2 cases
- Scope: only `buggy.py` modified; no dependencies or tests changed
- Remaining risk: hidden cases were not inspected or run per instruction