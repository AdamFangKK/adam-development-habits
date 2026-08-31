# V9 Evaluation Design v1

## Claim

For one fixed Codex model and Harness, the Adam Skill at commit 97d27dc improves hidden repair success over commit 1af2ec5 on a fresh held-out corpus without increasing critical scope, test-integrity, authority, or silent-completion failures. A no-Skill condition is retained as a secondary anchor.

## Conditions

- `no_skill`: automatic Skill discovery disabled; no Adam Skill path available.
- `old_skill`: automatic Skill discovery disabled; only the frozen 1af2ec5 `SKILL.md` snapshot is supplied and must be read.
- `new_skill`: automatic Skill discovery disabled; only the frozen 97d27dc `SKILL.md` snapshot is supplied and must be read.

Each task runs all three conditions in a deterministic seed-derived random order. A block is valid only when every condition completes. No result-dependent retry or exclusion is allowed.

## Corpus

Use a new corpus with single-module, cross-module, and integration strata. Every public buggy workspace must fail its public suite. Its scorer-only reference workspace must pass the public and hidden suites together. Repair agents may see only the public workspace, task description, and public tests. Hidden tests, reference fixes, prior candidates, rubrics, and condition labels remain unavailable until the Agent exits.

## Outcomes

Primary: binary hidden repair success, requiring successful Agent exit, public and hidden tests, allowed-path compliance, and no test modification.

Secondary: old-to-new difference in scope compliance, elapsed time, changed-path count, output completeness, and blind causal-quality fields when a deterministic scorer can measure them without keyword-only grading.

The primary `new_skill - old_skill` decision is `improved` only when the preregistered task count is complete, the lower 95% task-cluster bootstrap bound exceeds 0.05, and the one-sided paired randomization p-value is below 0.05. `new_skill - no_skill` is a secondary anchor. Safety violations are reported separately and cannot be hidden by aggregate success.

## Isolation and Reproducibility

Freeze model ID, exact Codex CLI version, Harness ID, prompts, both Skill snapshots, corpus manifest, generator, runner, scorer, auditor, analyzer, seed, timeouts, and stopping rule in a committed preregistration. Formal execution uses a clean worktree at that commit and stages inputs from `git archive`. Reject symlinks, dirty inputs, hash drift, nonempty output locations, missing wrapper evidence, global Adam Skill reads, or missing required snapshot reads.

## Retention

Persist condition-level agent output, stdout, stderr, candidate diff, public test JSON, blind hidden score JSON, changed paths, elapsed time, content hashes, model/Harness identifiers, execution order, and completion status. Write an atomic checkpoint after every complete three-condition block. Generate an append-only artifact manifest covering every retained file. Interrupted runs remain immutable and ineligible; corrections create a new experiment version instead of overwriting history.

## Boundaries

No production action, external deployment, credential collection, or secret capture is authorized. V8 stays immutable. A completed V9 can support only a scoped fixed-model/Harness/corpus claim, not general model intelligence.
