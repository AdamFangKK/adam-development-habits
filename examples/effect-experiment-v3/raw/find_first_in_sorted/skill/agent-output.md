Implemented the smallest bounds fix in [buggy.py](/private/tmp/adam-effect-find_first_in_sorted-skill-l14uiajo/buggy.py:3).

Evidence ledger:
- Owner: `find_first_in_sorted`
- Invariant: lowest matching index, else `-1`
- Diagnosis: invalid upper bound and non-progressing `hi = mid`
- Verification: `python3 test_public.py` → `2 public cases passed`
- Additional: 6 edge-case sanity checks passed; `git diff --check` passed
- Scope: only `buggy.py` modified; no tests or metadata changed; no commit made
- Remaining risk: none identified within the stated sorted-integer contract