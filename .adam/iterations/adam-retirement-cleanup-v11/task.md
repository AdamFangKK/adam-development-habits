# Automatic retirement checkpoint v11

Change level: 1
Canonical owner: `SKILL.md` section `Automatic Retirement and Drift Cleanup`
Affected callers/contracts: Codex Skill discovery, README and agent metadata consumers, retirement contract tests
In scope: make retirement cleanup an implicit Level 1/2 checkpoint; require owner reuse before implementation; detect semantic duplicates; synchronize explanatory and version metadata; stop completion on unresolved dynamic references
Out of scope: repository-wide dead-code deletion, new static-analysis dependencies, formal model-effect claims, production release actions
Acceptance criteria:

- A normal Level 1/2 change runs the cleanup checkpoint without an explicit user request.
- Existing owners are reused when their contract fits; semantic duplicates are identified using existing tooling or recorded structural/contract inspection.
- Candidates are classified as `remove`, `retain`, or `unknown`, and unresolved `unknown` paths block silent completion.
- Old symbols, behavior descriptions, comments, changelog/version text, and package metadata are synchronized in the same logical change.
- README and V9 experiment instructions contain no unqualified reference to an ungenerated preregistration artifact.
- Focused and full verification pass with no new dependency.

Invariant: no replaced or duplicate path is deleted without consumer, dynamic-lookup, compatibility, and contract evidence; no stale description teaches the retired contract.
Authority boundary: authorized local package edits only; no production or remote release action.
