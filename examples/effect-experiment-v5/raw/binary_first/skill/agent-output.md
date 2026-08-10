Change level: 1  
Canonical owner: `buggy.py:binary_first`  
Acceptance criteria: Return the first matching index, or `-1` for absent/empty inputs, in `O(log n)` time and `O(1)` space.  
Changed: Guarded the terminal lookup with `low < len(values)`.  
Removed or retained compatibility: No alternate path or dependency added.  
Safeguards: Preserved iterative bounded binary search.  
Quality decisions: Direct local fix; no API, data, dependency, or security changes.  
Delivery decisions: Only `buggy.py` modified; no commit performed.  
Verified: `python3 test_public.py` - `3 public cases passed`  
Verified: Million-element boundary stress probe - passed.  
Verified: `git diff --check` - passed.  
Independent review: Not required for this narrow Level 1 fix.  
Evidence artifact: Enforcement mode not enabled.  
Remaining risks: Inputs outside the sorted-list contract are untested.  
Causal conclusion: root-cause fix