Change level: 1  
Canonical owner: `buggy.py:prefix`

Acceptance criteria: Compute sums over half-open ranges `[start, end)`, including empty ranges.  
Changed: Replaced `sums[end - 1]` with `sums[end]`.  
Removed or retained compatibility: No compatibility paths or dependencies changed.  
Safeguards: Linear `O(n + q)` time and `O(n)` space retained.

Verified:
- `python3 test_public.py` - 1 public case passed.
- Deterministic 200,000-value/200,000-query stress probe - passed in `0.020573s`.
- Empty/negative edge probe - passed.
- `git diff --check` - passed.
- Only `buggy.py` modified.

Independent review: Not required for this narrow fix.  
Evidence artifact: Conversational ledger; machine enforcement not enabled.  
Remaining risks: Hidden invalid-input behavior remains unspecified; bytecode compilation was environment-blocked, but `python3 -B` execution passed.  
Causal conclusion: not activated