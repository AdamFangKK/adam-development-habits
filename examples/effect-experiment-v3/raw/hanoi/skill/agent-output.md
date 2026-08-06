Change level: 1  
Canonical owner: `buggy.py:hanoi`  
Acceptance criteria: Return shortest legal move lists matching the public contract.  
Changed: Corrected the destination peg and emitted list pairs.  
Removed or retained compatibility: No compatibility path added.  
Safeguards: No dependencies, I/O, or external state involved.  
Quality decisions: Direct implementation retained; not applicable otherwise.  
Delivery decisions: Only `buggy.py` changed; no commit made.  
Verified: `python3 test_public.py` - 2 public cases passed; `git diff --check` - clean; bounded heights 0-8 probe passed.  
Independent review: Not required for this narrow fix.  
Evidence artifact: Conversational ledger; no artifact mode enabled.  
Remaining risks: Hidden tests unavailable; output size is inherently exponential.  
Causal conclusion: not activated