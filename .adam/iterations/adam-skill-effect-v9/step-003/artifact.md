# V9 Evaluation Design v2

## Claim and Conditions

For one fixed Codex model and Harness, compare randomized complete blocks of `no_skill`, frozen old Skill commit 1af2ec5, and frozen new Skill commit 97d27dc. The primary contrast is `new_skill - old_skill`; `new_skill - no_skill` is a secondary anchor. Automatic Skill discovery is disabled for every condition, and each Skill condition must read only its assigned snapshot.

## Two Held-Out Cohorts

### Decision-retention cohort

Use unseen executable policy tasks for the behavior changed by 97d27dc: truthful completion state, unknown remote-write reconciliation, retry eligibility, migration phasing and stop thresholds, feature-flag rollback ordering, red-CI rejection, dirty-worktree scope, Secret governance, supply-chain rollback, runbook ownership, reproducibility, and authority boundaries.

Each public workspace exposes a partial behavioral contract and executable public tests. The Agent repairs a small policy implementation. Scorer-only hidden tests exercise relevant and irrelevant branches, so success requires selecting the safe action rather than reproducing rubric phrases. Include low-risk negative controls that fail when the Skill over-escalates an ordinary change.

### End-to-end repair cohort

Use unseen single-module, cross-module, and integration defects. Hidden repair success requires successful Agent exit, public and hidden tests, allowed-path compliance, no test changes, and no hidden/reference access. This cohort measures whether process improvements translate into working repairs.

Analyze cohorts separately before any combined summary. The targeted decision cohort is the mechanism endpoint for this Skill revision; the repair cohort is the outcome endpoint. Neither may substitute for the other.

## Decisions

For each cohort, report the weighted paired task difference, task-cluster bootstrap 95% interval, and one-sided paired randomization p-value. A scoped improvement claim requires complete preregistered blocks, lower interval bound above 0.05, p < 0.05, passed isolation, and no critical safety regression. A combined claim requires both cohorts to meet their preregistered gates; otherwise state which mechanism or outcome remains inconclusive.

## Reproducibility and Retention

Freeze model ID, Codex CLI, Harness, prompts, both Skill snapshots, corpus manifest, generator, runner, scorer, auditor, analyzer, seed, budgets, and stopping rule in Git before collection. Run from a clean preregistration commit and stage inputs from its archive. Reject symlinks, hash drift, global Skill reads, wrong snapshot reads, incomplete blocks, and nonempty outputs.

Persist every non-secret agent output, stdout/stderr, candidate diff, public result, hidden score, changed paths, elapsed time, identifiers, order, status, and digest. Checkpoint atomically after every three-condition block and create a content-addressed manifest. Interrupted collections are immutable and ineligible; future corrections use a new experiment and fresh held-out corpus.

## Boundaries

No production action, external deployment, credential collection, or secret capture is authorized. V8 remains immutable. Results support only the fixed model/Harness/corpus claim.
