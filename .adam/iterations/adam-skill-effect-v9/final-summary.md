# Final Summary for adam-skill-effect-v9

- Step count: 5
- Version count: 3
- Max rounds: 3
- Latest answer step: step-005
- Next allowed action: critique

## Latest Version

- Version: v3
- Step: step-005
- Solves: V9 physically separates Agent tasks, hidden tests, and references; scoring injects only allowlisted test files and verifies implementation hashes before and after injection.
- Remaining limit: No formal V9 model trial exists until implementation, commit, and preflight complete

## Version Trail

### v1 (step-001)

- What it solved: Initial baseline answer.
- Remaining limit: No critique yet.
- Why a next version was needed: A critique step must identify the primary bottleneck.

### v2 (step-003)

- What it solved: V9 now separates an executable decision-retention cohort from an end-to-end repair cohort and requires separate analysis before any combined claim.
- Remaining limit: The scorer file-layout boundary still requires implementation review before V9 can be trusted
- Why a next version was needed: One hidden-repair endpoint could not directly measure the concise Level 2 decision-retention behavior changed by the new Skill.
- Constraint on this version: Add one separately analyzed held-out decision cohort whose semantic scorer measures relevant safe decisions and unsafe commitments under a fixed concise-output budget.
- Preserved value: three-condition randomized blocks, blind hidden scoring, append-only artifact retention

### v3 (step-005)

- What it solved: V9 physically separates Agent tasks, hidden tests, and references; scoring injects only allowlisted test files and verifies implementation hashes before and after injection.
- Remaining limit: No formal V9 model trial exists until implementation, commit, and preflight complete
- Why a next version was needed: The inherited scorer could overwrite a candidate with reference implementation files and report a false hidden success.
- Constraint on this version: Separate reference and hidden-test trees, inject only allowlisted tests, and fail scoring if any candidate implementation hash changes during hidden injection.
- Preserved value: dual cohorts, three-condition causal comparison, blind post-exit scoring, append-only evidence retention
