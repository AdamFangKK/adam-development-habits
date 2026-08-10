Change level: 1  
Canonical owner: `buggy.py:fib_mod`  
Acceptance criteria: Standard Fibonacci modulo values; O(log n) time within one-second timeout.  
Changed: Replaced exponential recursion with iterative fast doubling.  
Removed or retained compatibility: Removed incorrect base cases; no compatibility path.  
Safeguards: Budget analysis and deterministic `n=100000` stress probe.  
Quality decisions: Direct implementation; no dependencies or abstractions.  
Delivery decisions: Only `buggy.py` modified; no commit or metadata changes.  
Verified: `python3 test_public.py` - 3 cases passed.  
Verified: Stress probe - `n=100000`, expected result `911435502`, completed in `0.000009s`.  
Verified: In-memory syntax check and `git diff --check` passed.  
Independent review: Not required for this Level 1 repair.  
Evidence artifact: Conversational ledger.  
Remaining risks: Negative `n` and zero modulus are unspecified and untested.  
Causal conclusion: root-cause fix