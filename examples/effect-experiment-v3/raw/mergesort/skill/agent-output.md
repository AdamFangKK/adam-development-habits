Change level: 1  
Canonical owner: `buggy.py:mergesort`  
Acceptance criteria: Correctly sort supplied cases, including singleton recursion boundaries.  
Changed: Base case now returns for lists of length `0` or `1`.  
Removed or retained compatibility: No compatibility paths changed.  
Safeguards: No additional safeguards applicable.  
Quality decisions: Direct minimal fix; no dependencies or abstractions.  
Delivery decisions: Only `buggy.py` modified; no commit made.  
Verified: `python3 test_public.py` - `4 public cases passed`; boundary probes passed; `git diff --check` passed.  
Independent review: Not required for this narrow fix.  
Evidence artifact: Enforcement mode not enabled.  
Remaining risks: None identified within the supplied contract.  
Causal conclusion: not activated