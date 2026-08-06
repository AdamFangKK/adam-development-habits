Repaired `get_factors` in [buggy.py](/tmp/adam-effect-get_factors-skill-chcqfoep/buggy.py:9) by retaining the final prime factor.

Evidence ledger:
- Change level: 1
- Baseline: public test failed on `100`, returning `[2, 2, 5]`.
- Verification: `python3 test_public.py` passed all 3 cases with the supplied one-second timeout.
- Scope: only `buggy.py` modified.
- Remaining risk: inputs outside the documented `n >= 1` precondition are not covered.