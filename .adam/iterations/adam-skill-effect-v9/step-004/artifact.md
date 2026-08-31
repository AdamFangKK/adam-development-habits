# V9 Design Critique 2

The inherited V6/V8 scorer boundary is invalid for capability measurement. The corpus hidden directory contains both reference implementation files and hidden tests, while `copy_hidden_tests` copies every hidden file into the candidate scoring copy. A direct reproduction showed that the unchanged buggy `iso_week_year_rollover` workspace fails its public test but receives a passing hidden score because the reference `calendar_key.py` overwrites the candidate.

V9 must physically separate public workspaces, scorer-only hidden tests, and reference workspaces. The blind scorer may copy only an allowlisted hidden-test subtree after Agent exit and must prove that implementation bytes are unchanged before and after injection. Reference workspaces are used only for corpus validation and may never be an input to candidate scoring.
