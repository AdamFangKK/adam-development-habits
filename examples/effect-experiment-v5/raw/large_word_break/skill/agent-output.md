Change level: 1  
Canonical owner: `buggy.py:word_break`  
Acceptance criteria: Correct word segmentation, empty text returns `True`, polynomial runtime within one-second cases.  
Changed: Replaced faulty recursive slicing with bottom-up reachability DP.  
Removed or retained compatibility: Removed exponential recursive path; no compatibility path needed.  
Safeguards:  
Shape: text length up to 260; DP positions are bounded by input length.  
Worst case: O(text length × word count × word length), O(text length) space.  
Bound: One-second per case; 260-character dense stress case completed in 0.010039s.  
Quality decisions: Direct implementation; no new dependencies or abstractions.  
Delivery decisions: Only `buggy.py` modified; no commit per request.  
Verified: `python3 test_public.py` - 3 public cases passed; `git diff --check` passed; 6 boundary cases passed.  
Independent review: Final diff inspected.  
Evidence artifact: Conversational ledger only.  
Remaining risks: Hidden tests unavailable; assumes iterable string words per supplied contract.  
Causal conclusion: root-cause fix