# Optional evidence reuse API

Use this reference only when a caller supplies evidence to the deterministic
planner. Normal Codex Skill use needs no JSON records or extra tooling.

The Python function and CLI facts JSON accept `context_revision` and
`evidence_records`. Each record has exactly these fields:

```json
{
  "capability": "risk_triage",
  "path": "/absolute/path/to/reviewed-output.txt",
  "sha256": "<64 lowercase hexadecimal characters>",
  "revision": "<same current input identity as context_revision>",
  "context_facts": ["level_1", "refactor"]
}
```

`context_facts` contains the current task facts excluding the catalog's produced
labels. Use an input identity covering relevant source, uncommitted changes,
configuration, catalog version, and runtime observations; a stale Git HEAD alone
is insufficient for changed worktrees or runtime data. The caller must check that
the actual artifact covers every claimed capability output. A file containing
the word "passed" is not a substitute for the observed command and result.

The planner checks schema, artifact hash, exact context, and revision equality.
Matching records produce `satisfied` statuses and reusable `verified_facts`;
changed/missing records appear in `invalidated_evidence` and are scheduled again
where applicable. This is an integrity check, not a semantic proof, timestamp
authority, or execution engine. `planned_facts` and `final_facts` may include
future outputs; `execution_status` remains `not_executed`.

Malformed facts or budgets raise an error. An ordinary blocked preview still
exits with code 0: inspect `blocked` and `deferred_mandatory` in its JSON. Existing
project test/CI evidence remains the completion authority.
