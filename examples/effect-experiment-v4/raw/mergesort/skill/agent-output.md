Change level: 1  
Canonical owner: [`buggy.py`](/tmp/adam-effect-mergesort-skill-mt6wg3b5/buggy.py:17) `mergesort`  
Acceptance criteria: terminate for empty/singleton inputs and return sorted lists without changing the public API.  
Changed: base case to `len(arr) <= 1`.  
Removed or retained compatibility: none; existing merge behavior remains.  
Safeguards: not applicable to this pure local function.  
Quality decisions: direct implementation; no dependencies, data ownership, or contract changes.  
Delivery decisions: no commit per instruction; no release, migration, configuration, or supply-chain impact.  
Verified: `python3 test_public.py` - `4 public cases passed` with the harness’s one-second per-case timeout. `git diff --check` - passed.  
Independent review: not required for this narrow repair.  
Evidence artifact: not created; edits were restricted to `buggy.py`.  
Remaining risks: public cases do not exhaustively cover all input types.  
Causal conclusion: not activated.