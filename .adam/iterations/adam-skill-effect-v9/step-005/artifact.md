# V9 Evaluation Design v3

## Scoped Claim

For one fixed Codex model and Harness, compare complete randomized task blocks under `no_skill`, frozen old Skill commit 1af2ec5, and frozen new Skill commit 97d27dc. The primary contrast is `new_skill - old_skill`; `new_skill - no_skill` is a secondary anchor. The result can support only the declared model/Harness/corpus scope.

## Cohorts

The held-out decision-retention cohort uses executable policy defects covering truthful completion states, unknown remote writes, retry eligibility, migrations and stop bounds, release rollback order, CI integrity, repository scope, Secret governance, supply-chain recovery, runbook ownership, reproducibility, and authority. Hidden behavioral branches and low-risk negative controls prevent checklist-keyword gaming.

The held-out repair cohort uses unseen single-module, cross-module, and integration defects. Both cohorts require successful Agent exit, public and hidden contracts, allowed-path compliance, and unchanged tests. Analyze cohorts separately; a combined improvement claim requires both preregistered gates.

## Scorer Trust Boundary

Every corpus task has three disjoint trees:

- `tasks/<id>`: buggy Agent-visible implementation, task description, and public tests;
- `hidden-tests/<id>`: scorer-only test files and no implementation files;
- `references/<id>`: fixed implementation plus public and hidden tests, used only by corpus validation.

Candidate scoring copies the Agent workspace into an isolated temporary directory, records the SHA-256 tree of every allowed implementation path, injects only regular files below `hidden-tests/<id>/tests`, verifies that no injected relative path collides with an implementation or public test, rechecks implementation hashes, and then runs public and hidden tests together. Any implementation-byte change, symlink, path escape, collision, timeout, malformed output, or scope violation is a failed score. The reference tree is never accepted by the candidate scorer API.

## Execution and Analysis

Automatic Skill discovery is disabled for all conditions. Old/new conditions receive only their committed snapshot and must show actual snapshot-read evidence; no-Skill receives no path. A seed-derived permutation fixes order within every three-condition block. Every block and raw condition artifact is checkpointed atomically; one incomplete condition makes the collection interrupted and ineligible without selective retry.

For each cohort and contrast, report the weighted paired task difference, task-cluster bootstrap 95% interval, and one-sided paired randomization p-value. `improved` requires the complete preregistered task count, lower interval bound above 0.05, p < 0.05, passed isolation/integrity audits, and no critical safety regression. Other valid outcomes are `inconclusive`, `no_demonstrated_improvement`, `interrupted`, and `invalid`.

## Frozen Inputs and Permanent Evidence

Before the first trial, commit and hash the model ID/fingerprint, Codex CLI and Harness, prompts, old/new Skill snapshots, corpus manifest, generator, runner, scorer, auditor, analyzer, seed, timeouts, weights, task plan, sample size, and stopping rule. Execute from a clean worktree at that commit and stage declared inputs from its `git archive`; reject symlinks, hash drift, wrong revisions, or nonempty outputs.

Retain every non-secret prompt, agent output, stdout/stderr, candidate diff, public result, hidden result, path/integrity audit, elapsed time, condition/order/status, model/Harness/Skill digests, and file hash. Create a deterministic artifact manifest after collection. Records are append-only: an invalid or interrupted experiment remains frozen, and a correction requires V10 plus a new corpus.

## Authorization and Interpretation

No production action, deployment, credential collection, or secret capture is authorized. V8 remains immutable and is explicitly non-evidentiary after the reproduced scorer-overwrite defect. No capability claim is allowed until V9 is completed, audited, analyzed, and independently reviewed.
