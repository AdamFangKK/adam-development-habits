---
name: adam-development-habits
description: "Use for AI-assisted code changes that need risk-scaled planning, causal diagnosis, failure semantics, retirement of obsolete or duplicate paths, synchronized documentation, stale-comment and metadata cleanup, evidence-oriented instrumentation, tests, security/performance safeguards, delivery controls, or machine-verifiable evidence. Trigger for features, bug fixes, refactors, integrations, reviews, migrations, configuration/secret/dependency changes, and maintenance of this Skill. 适用于开发、修复、重构、审查、迁移、清理废弃路径与过时说明、合理埋点与证据门禁。"
---

# Adam's Development Habits

Apply this workflow to every code change. Follow stricter repository instructions first. Keep changes focused and reversible. Do not add dependencies, abstractions, compatibility layers, or unrelated refactors without a concrete requirement. For Level 1 and Level 2 behavior changes, retirement and drift cleanup is implicit even when the user does not request it explicitly. If a replacement leaves behind a stale comment, README/API paragraph, release note, version string, or package metadata that still teaches the old contract, treat that text as part of the retired surface and update or delete it in the same logical change.

## Retirement Quick Gate

For every Level 1 or Level 2 replacement, inspect every existing non-test file in the changed boundary before editing and record two exact sets: (1) retired code identifiers, imports, exports, registry keys, flags, and paths; (2) old contract markers taken from source docstrings/comments and README/API/docs/changelog/release/version/metadata text. Before final verification, search every existing non-test file in the changed boundary, plus every changed explanatory surface, for every recorded value. Move real callers to the canonical owner, then remove the retired path and update or delete every remaining value. Do not finish while an old marker remains merely because a public test passes or a different retired identifier is gone. A document is a lead, not a consumer: retain an old path only for a named live runtime/API consumer or a verifiable external compatibility obligation with an owner, removal condition, observable signal, and coverage. If the scan finds an unresolved dynamic or external path, classify it `unknown` and stop completion rather than guessing.

## Operating Model

This skill is the policy layer, not a replacement for tests, static analysis, hooks, or CI. Use it to make the AI's reasoning and evidence explicit; use project tooling to enforce what can be automated.

Apply the lightest level that preserves confidence:

| Level | Scope | Required evidence |
|---|---|---|
| 0 | Documentation, comments, formatting, or an obvious one-line correction with no behavior change. | Inspect the diff and run the relevant narrow check. |
| 1 | Normal feature, bug fix, refactor, integration, or configuration behavior change. | Acceptance criteria, evidence ledger, relevant tests/checks, cleanup audit, and Causal Lite when the reported cause is unclear. |
| 2 | Public API, schema migration, authentication, money, privacy, concurrency, cross-service flow, architectural change, or broad refactor. | Level 1 plus a concise plan, rollback/compatibility strategy, failure-path tests, an independent review pass, and Causal Full for ambiguous failures or regressions. |

Do not downgrade a change to avoid evidence. If uncertain, use the higher level.

## Truthful Execution and Context Control

Use an explicit status for every material claim so a plausible plan cannot masquerade as completed work:

| Status | Meaning | Allowed claim |
|---|---|---|
| `planned` | Proposed approach or expected result; no command has run. | Say `计划` or `待执行`; never say fixed, tested, or passed. |
| `executed` | The exact tool or command ran and returned output. | Report the command, exit code, and observed result. |
| `verified` | The executed result was read and satisfies a named acceptance criterion. | Claim the criterion is verified, not that unrelated behavior is safe. |
| `blocked` | Execution was attempted but prevented by a missing dependency, authority, timeout, or reproducible failure. | State the blocker, attempted alternative, and residual risk. |

Never claim a file was changed, a test passed, a review happened, or a deployment completed from a patch, intention, expected output, or model confidence alone. Before editing, write a compact task contract: in-scope behavior, out-of-scope behavior, canonical owner, acceptance criteria, and authority boundary. At each phase boundary, reconcile the current diff and contract; if the request or repository context has drifted, stop and restate the active scope before continuing.

When a check fails, use a bounded repair loop: read the actual failure, classify the earliest responsible owner, make the smallest owner-level change, rerun the narrow check, then rerun the required full checks. Keep the same change evidence while the logical change continues. Stop only after all required checks pass, or after three consecutive attempts show the same external blocker; in the latter case report `blocked` with the exact evidence and do not claim completion. Do not hide a failing check by weakening a test, suppressing output, or changing the acceptance criterion.

Treat model capability and tool authority as boundaries. If the task depends on an unavailable API, visual inspection, production permission, hidden contract, or domain fact that was not verified, state the limitation and use `unknown` or `blocked`; do not fill the gap with a confident guess. Delegate or ask for an independent check when the missing capability materially affects safety or correctness.

## Causal Repair Card

When Causal Lite or Causal Full applies, complete this short card before proposing a repair. Keep it in the task record; it is deliberately front-loaded so an Agent can use the decision sequence before reading the detailed policy below.

1. Separate the observed **symptom** from the violated **invariant**.
2. Trace `trigger -> decision or state owner -> side effect -> symptom`; name the earliest candidate owner that can violate the invariant.
3. State one primary hypothesis and one plausible alternative. Run the lowest-risk discriminating probe that could reject the primary hypothesis.
4. Change the responsible decision or state owner, not the nearest downstream consumer, display, alert, or test expectation. Preserve a downstream guard only as an explicitly labeled mitigation.
5. Calibrate the conclusion to the evidence: an unrun, read-only, or in-memory-only counterfactual remains `Causal conclusion: unknown`.

## Budget-Aware Repair Gate

Activate this gate for any repair whose existing test command enforces a timeout, deadline, memory limit, query/call budget, or other resource bound, and for any algorithm whose work scales with a caller-controlled numeric dimension (capacity, range, recursion depth, input length, or number of states). A passing visible case proves only the observed inputs; it does not prove the implementation is safe at the declared boundary.

Before editing, write a three-line resource check in the evidence ledger:

```text
Shape: <caller-controlled dimensions and the current loop/recursion state space>
Worst case: <time, space, and failure mode at the largest credible input; unknown is explicit>
Bound: <the required timeout/memory/call budget and the algorithmic strategy that stays within it>
```

Then apply all of these rules:

- Treat hidden or production scale as unknown when only small examples are visible. Do not preserve recursion, repeated slicing, or a table indexed by an unbounded numeric value merely because public tests pass.
- Prefer a complexity bound expressed in input size (or a sparse representation of reachable states) over a bound proportional to a raw numeric magnitude. If the contract makes a numeric bound unavoidable, state it and reject inputs outside it rather than silently allocating unbounded memory.
- Run the supplied checks plus one deterministic stress probe that is larger or structurally harder than the largest visible case while remaining inside the declared contract. Record the command, elapsed time or resource result, and the remaining untested boundary. If no safe probe can be constructed, record `budget unverified` and do not claim the optimization is complete.
- Separate semantic repair from performance repair: first preserve the public invariant, then verify that the candidate algorithm meets the budget. A minimal condition-only patch is incomplete when the original algorithm still violates the resource bound.

For functions with multiple valid outputs, verify the mathematical contract (validity plus optimality) rather than treating one reference rendering as the only answer. A scorer or test that cannot express the contract is a test limitation, not evidence that a correct alternative is wrong.

## Causal Execution Discipline

Use this discipline to avoid patching the nearest symptom instead of the responsible behavior. It is a diagnosis workflow, not a requirement to prove causality for every feature or obvious correction.

Activate it for an unclear bug, a regression, a performance or reliability degradation, an intermittent failure, or a suspected interaction across a service, deployment, configuration, dependency, or concurrency boundary. Do not activate it for Level 0 work or a behavior change whose cause and owner are already established by a narrow check.

For **Causal Lite**, before the first edit, record:

- the observed symptom, separated from any interpretation of its cause;
- one primary hypothesis and at least one plausible alternative;
- a discriminating check that could weaken or reject the primary hypothesis; and
- the actual result of that check, or why the check is unavailable.

For **Causal Full**, also identify the upstream call, data, configuration, or dependency path; inspect the relevant change or release timeline; and reproduce the failure or run an isolated intervention when that can be done safely. Map the path as `trigger -> decision or state owner -> side effect -> symptom`, then name the first decision or state transition that diverges from the invariant. Record one minimal counterfactual intervention that changes that candidate while holding adjacent inputs and dependencies fixed, its expected result, its actual result, and which plausible alternative remains rejected or unresolved. Use read-only observation and local test/worktree experiments by default. Do not perform production experiments without explicit authorization. End every Causal Full response with one exact line: `Causal conclusion: root-cause fix`, `Causal conclusion: mitigation`, `Causal conclusion: instrumentation-only`, or `Causal conclusion: unknown`. If the counterfactual was only proposed, unrun, unavailable, or the task is read-only, that line must be exactly `Causal conclusion: unknown`. A read-only diagnosis remains unknown even if it runs an in-memory probe: only an authorized code-changing worktree experiment with the candidate diff and before/after command output recorded can support a root-cause fix. In that state, call the owner only a candidate and do not describe the overall causal conclusion as `root cause`, `root-cause owner`, `confirmed`, or `high confidence`; confidence may qualify an individual observation only.

**Causal Full preflight gate:** before writing the terminal line, state `Execution authority: read-only` or `Execution authority: authorized code-changing worktree`. State `Counterfactual status: unrun`, `in-memory-only`, `proposed`, `blocked`, or `executed`. Treat an in-memory patch, pseudocode, expected output, or test run against unchanged source as `in-memory-only`, not an intervention. The terminal line may be `root-cause fix` only when the response records an authorized code-changing worktree, a candidate diff, and before/after command or test output from that changed worktree. If any one is absent, use exactly `Causal conclusion: unknown`; do not call the candidate owner confirmed or call the result a root-cause fix. This gate applies even when the unchanged fixture reproduces the symptom and an in-memory simulation produces the expected result.

For an ambiguous remote create, update, charge, send, or enqueue operation, treat reconciliation as a three-state contract: confirmed, definitively absent, or unknown. Retry the write only when the dependency establishes definitive absence or returns a pre-acceptance rejection explicitly classified as retryable. Persist a terminal rejection with its safe reason as failed, acknowledge or dead-letter it only after that transition is durable, and do not revive or alter it on redelivery. When reconciliation is unknown, unavailable, delayed, or ambiguous, preserve the durable pending record; do not acknowledge it as successful, and acknowledge only after a deduplicated recovery job has been durably scheduled when queue semantics require that handoff. Persist and verify a canonical operation identity that includes the business event plus every side-effect-defining dimension, such as tenant, recipient, resource, amount, payload version, or content hash. A matching business-event ID alone is not enough to reuse a prior result safely: re-verify that identity at provider confirmation, acknowledgement, dead-letter, and recovery-handoff boundaries. Record the reconciliation class and retry decision with trace/correlation IDs, without payload content or personal data.

For a remote-write candidate, make a small state table before calling it safe: `FOUND` confirms only a matching canonical identity and may finalize/ack; `ABSENT` may issue a new idempotent send; `UNKNOWN` preserves pending with no send or ack; a retryable **pre-acceptance** rejection restores the state required for a later attempt; and a terminal rejection becomes durable failed work. Test each branch and at least one identity mismatch. If a counterfactual is only proposed or its result is unrun, the causal conclusion is `unknown`; never label a design, diff, or expected outcome a root-cause fix or a high-confidence causal result.

Treat evidence in descending order of strength: observation establishes correlation, reproduction establishes repeatability, and an isolated intervention supports a causal claim. Git history, blame, and temporal proximity are candidate evidence only; they do not prove a root cause.

Classify the conclusion precisely:

- **root-cause fix**: the changed behavior lies at the named causal owner, the minimal counterfactual intervention removes the reproduction, and the evidence does not leave an equally plausible untested upstream owner;
- **mitigation**: the change reduces impact but the responsible cause remains unproven;
- **instrumentation-only**: the change adds evidence collection without altering the failing behavior; or
- **unknown**: the available evidence cannot distinguish the hypotheses.

Do not call a downstream display, retry wrapper, test expectation, or alert-suppression change a root-cause fix merely because it hides the symptom. Classify it as mitigation unless it changes the responsible decision or state transition and the counterfactual evidence supports that link. When evidence is insufficient, prefer instrumentation, a minimal reproducer, a reversible guard, or escalation over a speculative behavioral change. Keep the hypothesis set small and choose the lowest-risk check that best distinguishes it; do not create analysis theatre by enumerating arbitrary possibilities.

## Measuring Skill Effect

Use this protocol only when claiming that enabling this Skill improves repair success or causal-analysis quality. A finite experiment cannot prove an overall model capability. It can support only a scoped statement about a fixed model, Harness, Skill revision, corpus, and independent hidden scorer.

Before running an effect experiment, pre-register the hypothesis, primary metric, practical minimum effect, task IDs, strata and weights, fixed pairs per task, deterministic randomization seed/order, stopping rule, fixed model/Harness and Skill-revision identifiers, corpus manifest hash, baseline and Skill prompt hashes, and hidden-scorer hash. Freeze the whole envelope in Git before the first trial. The only planned condition difference is Skill activation; run both conditions for every task in the registered order. Keep reference fixes, hidden tests, rubric, prior candidate outputs, and condition labels unavailable to the repair agent and blind scorer. Do not drop interrupted, inconvenient, or failed planned tasks after seeing an outcome; declare the experiment incomplete instead.

Use hidden repair success as the primary metric. A blind causal-evidence score may be secondary, never a substitute for the hidden contract. Cluster repeated runs by task rather than treating them as independent evidence. Analyze completed records with [scripts/analyze_skill_effect.py](scripts/analyze_skill_effect.py) and [examples/skill-effect-preregistration.json](examples/skill-effect-preregistration.json): it reports `improved` only when the preregistered task count, lower 95% confidence bound above the practical threshold, and paired randomization threshold all pass. `inconclusive` and `no_demonstrated_improvement` are valid outcomes, not permission to re-label a result.

When a result is not improved, retain raw artifacts and classify each failure before changing the Skill: missed owner, untested alternative, shallow public-test repair, hidden-contract failure, unsafe side effect, scope expansion, or tool/authority violation. Change the smallest rule that addresses a repeated category, then pre-register a new Skill revision and use a fresh held-out corpus. Do not tune against a hidden set and claim its retest is independent. Read [references/effect-evaluation.md](references/effect-evaluation.md) for the full protocol and isolation limits.

## Project Constitution and Acceptance Criteria

Before a Level 1 or Level 2 change, read existing repository instructions, conventions, architecture documents, and CI configuration. Treat them as the project constitution.

For a Level 2 change without an explicit local rule, write a concise constitution statement in the task record or plan:

- non-negotiable domain and security invariants;
- compatibility and data-migration boundaries;
- approved dependencies and architectural patterns;
- release, rollback, and observability expectations.

Define acceptance criteria before implementation. Include the success behavior, important failure behavior, compatibility expectations, and the verification that proves each one. A request is not complete merely because its happy path works.

## Non-Negotiable Completion Gate

Do not claim a code task is complete until all applicable items below have evidence:

- the canonical implementation path and affected callers were identified before editing;
- acceptance criteria and behavior-preserving invariants were defined;
- the applicable retirement sweep classified touched or replaced paths as `remove`, `retain`, or `unknown`, with evidence for each decision;
- changed behavior, tests, configuration, telemetry, comments, and documentation describe the same current contract;
- when Maintainable Boundaries and Atomic Design applies, the owner, contract, error outcome, side effect or state transition, dependency direction, and extension decision are recorded and reviewed;
- when mutable data, a public contract, operational behavior, performance, or security is material, ownership, lifecycle, failure semantics, compatibility, budget, and threat boundary are recorded and reviewed;
- when Delivery Lifecycle and Repository Hygiene applies, the commit or PR scope, release/recovery, migration, configuration or secret, dependency, operational-knowledge, and reproducibility decisions are recorded and reviewed;
- when Causal Execution Discipline was active, the conclusion is supported by recorded evidence and is labeled as a root-cause fix, mitigation, instrumentation-only, or unknown;
- every replaced path was removed, or each retained path has a real consumer, removal condition, and coverage;
- relevant safeguards were implemented or explicitly shown to be not applicable;
- the exact verification commands were run and their outcome was read;
- the final report records changed files, removed code, verification evidence, and remaining risks.
- the final report records the retirement classification and documentation synchronization result for the changed boundary.

Never use "should work", "likely", or an unrun command as completion evidence. A failed or unavailable required check is a blocker, not a passing result.

## Evidence Ledger

For every Level 1 or Level 2 change, create a concise ledger before the first edit and update it before completion:

```text
Change level: <0|1|2>
Canonical owner: <file and symbol or route>
Affected callers/contracts: <files, consumers, or none>
Acceptance criteria: <success, failure, and compatibility conditions>
Invariant: <behavior that must remain true>
Replaced paths: <what will be removed, or none>
Retained compatibility: <consumer + removal condition + test, or none>
Retirement sweep: <remove/retain/unknown decisions for touched or replaced paths + evidence>
Documentation synchronization: <updated/deleted/confirmed-current README, API docs, ADR, runbook, examples, comments, version/metadata descriptions>
Instrumentation: <not applicable with reason, or event boundaries/schema, redaction/cardinality review, tests and runtime/development evidence>
Safeguards: <applicable items from the matrix>
Verification: <commands run and actual results>
Causal diagnosis: <not activated, or symptom + hypotheses + causal owner + counterfactual intervention + discriminating evidence + conclusion>
Design boundary: <owner, contract, error outcome, side effects/state transition, or not applicable>
Dependency audit: <new or changed dependencies, allowed direction, or not applicable>
Extension decision: <real consumer/contract and test, or deliberately direct implementation>
Data ownership: <authoritative owner, lifecycle/privacy boundary, or not applicable>
Error model: <stable outcome classes, retry/unknown policy, or not applicable>
Contract evolution: <compatibility, migration/rollback, consumer test, or not applicable>
Operational budget: <SLO/performance/resource/security signal and response, or not applicable>
Delivery lifecycle: <atomic commit/PR scope, pre-merge checks, or not applicable>
Release and recovery: <flag/rollout/monitoring/rollback evidence, or not applicable>
Data migration: <expand-migrate-contract/backup/restore evidence, or not applicable>
Configuration and secrets: <owner/default/precedence/schema/access evidence, or not applicable>
Supply chain: <dependency necessity/license/security/lockfile/removal evidence, or not applicable>
Operational knowledge: <ADR/API change/runbook/regression record, or not applicable>
Reproducibility: <setup/tool-version/minimal-data/clean-run evidence, or not applicable>
```

Use narrow searches to establish the ledger. Check imports, exports, registrations, routes, configuration keys, message names, tests, and dynamic lookup conventions. Never infer that code is dead only because a direct reference search is empty.

## Automatic Retirement and Drift Cleanup

This is the default maintenance behavior for normal development. The Agent performs it as an internal checkpoint; it must not wait for the user to ask for cleanup explicitly. It is scoped to the paths touched, replaced, or made non-canonical by the current logical change; it is not permission for an unrelated repository-wide cleanup.

Treat stale explanatory surfaces the same way you treat stale code. A comment, README paragraph, API description, changelog entry, version note, example, or package metadata item that still describes the retired contract is obsolete once the canonical owner changes. It must be updated or deleted in the same logical change unless a real consumer or compatibility obligation is proven.

| Practice | Trigger | Level 0 | Level 1 | Level 2 | Evidence |
|---|---|---|---|---|---|
| Automatic retirement and drift cleanup | A feature, bug fix, refactor, optimization, rename, contract/configuration/flag/dependency change, or any change that introduces a replacement or makes an earlier path non-canonical. Level 0 never triggers a full sweep. | No full sweep; only correct directly edited text when the requested no-behavior change requires it. | Run a light sweep over the changed boundary: implementation, callers, tests, types/exports, dependencies, routes/registrations, configuration/flags, telemetry, docs/examples, comments, and version/metadata descriptions. Classify candidates as `remove`, `retain`, or `unknown`; delete confirmed leftovers and update stale descriptions in the same change. | Run the complete sweep, including dynamic loading/registration, jobs/queues, generated entry points, compatibility shims, migration state, API/ADR/runbook references, and independent review. Retained paths require a real consumer, removal condition, observability, and coverage; unresolved dynamic paths stay `unknown` until checked. | Search/import or call-graph output, registration/config lookup, static-analysis or dependency scan, final diff, focused tests/CI, migration or rollback rehearsal when applicable, documentation review, and ledger/report entries. |
| Development and runtime instrumentation | A Level 1/2 change has an observable state transition, external boundary, performance/reliability budget, cleanup decision, or more than one execution phase. Pure documentation and isolated pure functions without an operational signal do not trigger application telemetry. | No new telemetry; do not add instrumentation solely to satisfy the policy. | Add lightweight, structured, low-cardinality events at the changed decision/state boundary and failure/timeout path; include correlation/change ID, outcome, elapsed time or count, and redacted reason. Record the Skill checkpoints `owner_located`, `retirement_classified`, and `verification_completed` in the evidence ledger or existing event sink. | Add complete boundary coverage for plan/start, owner selection, replacement/cleanup classification, retained/unknown resolution, verification, rollout/rollback or recovery, and terminal failure; define metric names, owner, threshold, sampling/retention, and alert action. Validate that telemetry is emitted once per logical transition, is safe under retry/concurrency, and does not contain secrets, payloads, or unbounded labels. | Event schema or existing telemetry definition, focused tests asserting event name/outcome/redaction/cardinality, command output or CI artifact showing checkpoint events, and runtime metrics/trace export when available. |

Use this checkpoint in order for every Level 1 or Level 2 change:

1. **Before implementation**, locate the canonical owner by responsibility and inspect nearby utilities, adapters, exports, and extension points. If an existing owner already satisfies the contract, mark the candidate `reuse_existing_owner` and extend or call it; do not create a parallel implementation merely because it is shorter to write.
2. **After implementation and before the final verification/commit**, search the changed boundary for duplicate or superseded paths. Prefer the repository's existing duplicate-code or static-analysis tool; when none exists, compare the normalized control flow, input/output contract, and call sites rather than relying on names alone. Record the command or inspection result.
3. **Write a retirement inventory before deleting anything**: `path | role | owner | direct consumers | dynamic/generated/external lookup | evidence | classification | removal condition`. Include source files, test fixtures, exports, configuration/flags, registrations, telemetry, docs, examples, version metadata, and comments when they describe the changed contract. This keeps a deleted implementation from surviving as an orphaned adapter, fixture, flag, dashboard label, or misleading explanation.
4. **Classify each candidate** as `remove`, `retain`, or `unknown`. A semantic duplicate that has no independent contract is `remove` after callers move; a real compatibility consumer is `retain`; a dynamic, generated, or external path is `unknown` until its lookup or runtime use is checked. A file deletion is valid only when the deleted path is listed in the change scope and the post-change import/registration/configuration checks pass.
5. **Synchronize descriptions in the same change**: search old symbols, old behavior phrases, configuration keys, flag names, telemetry labels, version notes, changelog entries, examples, and package metadata. Update or delete stale explanatory text; do not leave a comment or release description teaching the retired contract. Prefer the current source/contract as the authority for README, API descriptions, ADRs, runbooks, and version notes; do not hand-edit a version/status claim that cannot be tied to Git or CI evidence.
6. **Run a post-retirement orphan scan** after deletion: verify no active import/export/registration/configuration/telemetry reference points to the removed path, no stale contract phrase remains outside tests/history, and the clean checkout or repository test command still discovers the intended entry points. Treat generated files and convention-based loaders as separate evidence classes, not as ordinary text matches.
7. **Stop the completion gate when evidence is unresolved**. Do not silently retain an unknown path or report the change complete. Run a targeted registration/runtime/configuration check, or report the exact unresolved path and residual risk as `blocked`/`unknown`.

### Instrumentation Checkpoint

Instrumentation is part of the affected implementation surface when the changed boundary has a measurable runtime or development outcome. First discover the repository's existing logger, metrics, tracing, audit, and evidence conventions and reuse them; do not add a new telemetry dependency or a second event vocabulary. Use stable event names and bounded labels such as `change_id`, `component`, `operation`, `outcome`, `classification`, and `error_class`; never record secrets, raw payloads, personal data, source text, or user-controlled label values.

At Level 1, place the smallest useful probes at the decision or state-transition owner, its timeout/error path, and the verification boundary. At Level 2, cover the full lifecycle (`started -> owner_located -> implemented -> cleanup_classified -> verified -> committed`), retries/concurrency and recovery/rollback branches when applicable, and define the metric owner, threshold, sampling/retention, and response. A probe must have a question it answers and a test or command that proves it emits the expected redacted event; do not add noisy line-by-line logging. For a pure local helper with no operational signal, record `Instrumentation: not applicable` with the reason.

The process-level checkpoint event payload should be machine-readable and bounded:

```text
event: <stable checkpoint name>
change_id: <non-secret logical change ID>
component: <canonical owner>
outcome: <planned|executed|verified|blocked>
classification: <remove|retain|unknown|reuse_existing_owner|not_applicable>
duration_ms: <optional non-negative number>
evidence_id: <ledger artifact ID when available>
```

Do not treat an emitted event as proof that the behavior is correct: pair it with the command, test, CI, trace, or runtime metric that answers the underlying acceptance criterion. Missing telemetry from an applicable boundary is a verification gap; unresolved dynamic instrumentation or redaction behavior remains `unknown` rather than silently complete.

When event output is available as JSONL, validate it with the package's standard-library checker, `python3 scripts/validate_development_events.py --events <events.jsonl> --level <0|1|2>`. Treat a non-zero result as a verification failure; do not weaken the checker to make an unsafe event stream pass.

Before editing, record the canonical owner, affected callers/consumers, and every path expected to be replaced. Search for an existing owner, utility, extension point, or adapter before adding another implementation. Reuse or extend the owner when its contract and boundary fit; do not create a third implementation to avoid reading the existing one.

After editing, perform the retirement sweep and classify every candidate:

- `remove`: the new owner handles the responsibility, no real consumer or compatibility obligation remains, and imports, registrations, dynamic lookup, configuration, tests, docs, and telemetry checks support deletion;
- `retain`: a named consumer or compatibility obligation still exists. Record the consumer, expiry/removal condition, observable signal, and compatibility or integration test. A vague “might be used” is not evidence;
- `unknown`: a dynamic, generated, external, or otherwise unresolved reference may exist. Do not delete it or call the change complete until a targeted runtime/registry/configuration check resolves it, or report the residual risk explicitly.

A comment, README/API paragraph, changelog, release note, version description, example, or package metadata item is **not a consumer by itself**. It may be a lead to investigate or a description that must be synchronized, but it cannot independently justify `retain`. Retain an old path only after naming a live runtime/API consumer or a verifiable external compatibility obligation, then recording its owner, removal condition, observable signal, and coverage. A published compatibility commitment may be evidence when its authoritative contract, owner, and expiry are identified; a stale or unverified project document is not such a commitment. When no real consumer or obligation is established, update or delete the stale description and classify the superseded path as `remove`.

Treat the whole contract as one implementation surface. When a path is removed or renamed, remove or update its tests, fixtures, types, exports, dependency entries, routes, jobs, queues, flags, environment keys, telemetry labels, README/API docs, ADRs, runbooks, examples, comments, version descriptions, and Skill/package metadata as applicable. A comment or version note that describes the old decision is stale code in another form and must be revised or deleted in the same logical change.

Do not use a zero direct-reference result, a `deprecated` keyword search, or a green public test alone as proof of retirement. Do not preserve an unconsumed compatibility layer merely because deletion feels risky, and do not guess-delete a path whose dynamic usage is unresolved. A missing-file result is evidence of deletion only when the path was in scope and the post-retirement orphan scan is clean. If the sweep finds no candidate, record `none found after scoped search` and the commands or tools used.

When Causal Execution Discipline is active, add the symptom, hypotheses, discriminating check, evidence strength, conclusion classification, confidence, and any stop reason to the ledger. For Causal Full, also record the upstream path, named causal owner, minimal counterfactual intervention with expected and actual outcomes, the relevant change, release, or runtime timeline, and any rejected or unresolved alternative. In machine-enforced evidence mode, declare each referenced local evidence artifact by ID, repository-relative path, SHA-256 digest, and summary; reference only declared IDs from hypotheses. A root-cause fix must reference a hash-verified execution artifact such as command output, test output, or a trace export; source code alone is insufficient. A causal conclusion must link to actual command output, test output, trace data, or an equivalent artifact; a narrative assertion is not evidence.

## Evidence Enforcement Mode

Use the conversational ledger by default. A repository opts into machine-enforced evidence only when it contains an `.adam/` directory or the user explicitly requests enforcement.

For an opted-in repository, create one unique `.adam/evidence/<change-id>.json` artifact for every Level 1 or Level 2 logical change. Start from [assets/evidence-ledger.example.json](assets/evidence-ledger.example.json), then validate it with the project-local evidence script before completion. Update an existing artifact only while continuing that same change in the same branch or pull request. Keep the artifact in the same pull request as the code change.

The artifact records facts after verification; it does not replace tests or let a failed command become passing by declaration. For a Level 2 change, include rollback or compatibility strategy and an independent review outcome.

Author new machine-enforced evidence as `schema_version: 2`. Version 2 requires every ledger decision in `quality_decisions`: `design_boundary`, `dependency_audit`, `extension_decision`, `data_ownership`, `error_model`, `contract_evolution`, `operational_budget`, `threat_boundary`, `delivery_lifecycle`, `release_recovery`, `data_migration`, `configuration_secrets`, `dependency_supply_chain`, `operational_knowledge`, and `reproducibility`. Each entry uses `applied` or `not_applicable` with a concrete rationale. It also requires every passed verification to reference a hash-verified `command_output` or `test_output` for the same command, with exit code, UTC execution timestamp, and repository revision; every Level 2 independent review must identify a reviewer other than the implementer and reference a hash-verified `review_report`. Schema version 1 is read-only compatibility for existing historical records; it remains individually valid but cannot satisfy the changed-evidence gate for new behavioral work.

By default, a supporting artifact path and SHA-256 bind to the current worktree. When an existing evidence record intentionally cites an older file revision, add its full lowercase `git_commit`; the validator then reads and hashes that path from the declared commit instead of silently rebinding history to current bytes. Do not add `git_commit` merely to make a stale artifact pass: first prove that the declared digest exists at that commit and still represents the recorded decision. A hash link proves artifact identity, not that its summary is true or that its command ran; retain executable project checks and CI as the factual authority.

## One Active Implementation

Use [Automatic Retirement and Drift Cleanup](#automatic-retirement-and-drift-cleanup) for the trigger and evidence depth; this section states the implementation rule.

1. Locate the existing owner of the behavior before adding code.
2. Modify the canonical owner in place when possible.
3. When replacing behavior, move every caller, then delete the old implementation and its references in the same change.
4. Remove obsolete tests, types, routes, jobs, queue consumers, configuration, feature flags, documentation, examples, and telemetry labels.
5. Preserve an old path only for a verified external compatibility or controlled rollout requirement. Record its consumer and deletion condition in the ledger.

Do not leave commented-out code, duplicate business rules, unused helpers, unused imports or exports, abandoned feature flags, dead endpoints, speculative abstractions, or two implementations that claim the same responsibility.

## Maintainable Boundaries and Atomic Design

Apply this discipline to a new or restructured business module, a cross-module responsibility change, an extension point, or a Level 1 or Level 2 change whose readability or coupling is material. Do not use it to force a style-only rewrite or an architecture framework into a small, local change.

- Make names express domain intent, ownership, and outcomes. Keep non-obvious mutation, I/O, retry, authorization, and error behavior explicit at the boundary that owns it.
- Give every changed module one coherent business responsibility and a small public contract. A unit may compose several adjacent steps; "atomic" means one decision or one recoverable state transition, not an arbitrary line-count target or a proliferation of tiny functions.
- Separate deterministic policy from irreversible effects when practical: put storage, transport, clocks, randomness, and process-wide mutable state behind a narrow boundary. Do not hide domain decisions inside request handlers, ORM callbacks, framework hooks, or generic utility modules.
- Define who owns each mutable state transition. Commit related state atomically when one transaction is available; otherwise document ordering, idempotency, recovery, and compensation or outbox behavior. Do not present multiple independent writes as atomic merely because they occur in one function.
- Make dependency direction visible. Keep domain policy at the narrowest boundary that owns it, and avoid introducing transport, presentation, or storage coupling unless the existing repository architecture requires it; adapters may depend on domain contracts. Do not add cycles, bidirectional coordination, shared mutable globals, reach-through access to another module's internals, or a catch-all `utils` dependency without an explicit owner and review rationale.
- Keep interfaces concrete until a real need exists. Add an abstraction only for two independent consumers, a stable external contract, or a demonstrated testing boundary. Record the consumer or contract and add a contract or integration test when it is public, versioned, or implemented by multiple adapters.
- Extend a contract by compatible addition when possible. Preserve validation and ownership at the boundary, version a public contract when required, and do not use a broad refactor to smuggle in unrelated extensions.

For applicable Level 1 and Level 2 changes, add these concise entries to the evidence ledger:

```text
Design boundary: <owner; input/output contract; error outcome; side effect or state transition>
Dependency audit: <changed edge; permitted direction; cycle/private-state check>
Extension decision: <second consumer or stable contract + test; otherwise why direct code remains>
```

During review, ask whether a reader can identify the owner, input/output contract, state change, error outcome, dependency direction, and extension decision without tracing unrelated modules. Prefer a direct implementation when it is clearer; reduce coupling at the actual boundary rather than adding indirection inside one module.

## Failure Semantics and Data Ownership

Apply this discipline whenever a change creates, changes, deletes, retains, synchronizes, or exposes mutable business or personal data, or when a dependency can fail after a local decision.

- Name the authoritative owner for every mutable business fact. Other modules consume a contract, cache a derived view, or own a separate fact; they must not silently become a second source of truth.
- Define the lifecycle at the owner: creation, valid transitions, retention, archival or deletion, and access boundary. Minimize collected data, record a lawful retention or deletion rule when applicable, and do not put personal or secret data in ordinary logs, identifiers, metrics, or errors.
- Classify failures at system boundaries as validation/precondition, authorization/ownership, domain conflict, transient dependency, terminal dependency, or unknown outcome. Return a stable safe code or typed outcome; preserve the underlying detail only in redacted diagnostics.
- State retry eligibility, attempt bound, idempotency key, deadline, and recovery owner. An unknown remote-write result is not a retryable failure by default; follow the three-state reconciliation discipline.
- Make cancellation, timeout, resource cleanup, and partial-result behavior explicit for long-running work. Do not continue side effects after a cancelled or expired request unless a durable background handoff owns them.

## Contract Evolution and Test Quality

Apply this discipline to public APIs, events, schemas, configuration contracts, shared libraries, and behavior with more than one consumer.

- Treat each public request, response, event, schema, configuration key, and error code as a contract. Prefer compatible additions with documented defaults; version or migrate breaking changes deliberately and define rollback before mutating production data.
- Identify known consumers before removing, renaming, tightening validation, changing defaults, or altering event semantics. Retain a compatibility path only with a consumer, expiry condition, observability, and coverage.
- Test business outcomes and invariants at the public or module boundary, not only private method calls or mocks. Cover representative success, validation, authorization, conflict, retry/unknown, and compatibility behavior.
- Use contract or integration tests for public APIs, events, schema migrations, and multiple adapters. Use property, table-driven, or boundary-value tests when rules have broad input spaces; do not confuse a large test count with independent coverage.
- Keep tests deterministic: control time, randomness, concurrency scheduling, external I/O, and test data ownership. Treat flaky tests as defects; find the shared state, timing, or nondeterministic dependency instead of normalizing retries.

## Operational Readiness, Performance, and Security

Apply the relevant parts to deployable services, exposed workflows, expensive operations, privileged data, or a change with a measurable latency, cost, availability, or abuse risk.

- Define the observable user or business outcome, a baseline when changing performance, and a budget appropriate to the path: latency percentile, throughput, error rate, queue age, query/external-call count, memory, or cost. Measure before and after optimization; do not call an optimization successful without evidence.
- Emit redacted structured logs and low-cardinality metrics that distinguish outcome classes. Propagate traces across boundaries; make alerts actionable with an owner, threshold, and a response or runbook rather than alerting on every exception.
- Bound untrusted work with payload limits, pagination, deadlines, concurrency limits, rate limits, backpressure, and cancellation. Confirm that cache, retry, and fallback behavior preserve authorization and data freshness requirements.
- Perform a proportional threat check for exposed or privileged behavior: trust boundary, authentication, authorization, tenant/resource ownership, input validation, secret handling, sensitive-data exposure, abuse path, and auditability. Do not rely on client-side controls for server authorization.
- For a Level 2 security, privacy, public-contract, money, or operational change, require an independent review that explicitly covers these boundaries.

## Delivery Lifecycle and Repository Hygiene

Apply only the triggered rows below. Level 0 work does not trigger this section. For Level 1, record the named decision and execute the narrowest available local or CI check. For Level 2, create a concise plan before implementation, retain the corresponding evidence, and use an independent review. Reuse the repository's existing Git, hosting, CI, deployment, migration, secret, dependency, and documentation tools; do not add a dependency or external service merely to satisfy this policy.

| Practice | Trigger | Level 1 | Level 2 | Evidence |
|---|---|---|---|---|
| Atomic Git change and PR | A Git-tracked behavior, configuration, test, or documentation change | Keep one coherent, reviewable scope; inspect the diff and complete required checks before committing. Do not commit secrets, generated credentials, or unrelated edits. | Create an atomic commit after verification. Where the repository uses PRs, keep the PR small and state scope, acceptance criteria, risk, rollback, and verification; CI is the minimum merge bar and must not be bypassed. | `git status`, diff/check output, commit ID, PR/CI result, or a recorded reason the repository has no PR workflow. |
| Release and recovery | Deployable service, user-facing rollout, feature flag, or operational configuration change | Name the release owner, observable outcome, stop condition, and rollback mechanism. | Define rollout stages, monitoring window, thresholds, rollback steps, and recovery owner; rehearse or test rollback when the change can cause user or data impact. Do not perform production release actions without authorization. | Existing deployment/flag configuration, CI or staging output, rollout metrics, rollback test, or explicit residual risk. |
| Data migration | Schema, persistence format, backfill, retention, or data transformation change | State forward compatibility, backout path, data owner, and migration-test or dry-run result. | Use expand-migrate-contract: add compatible representation, migrate or backfill, switch readers/writers, then remove old state only after consumer and recovery evidence. Validate backup/restore for destructive or irreversible work. | Migration plan, dry-run/test output, compatibility tests, backup/restore evidence, and cleanup condition. |
| Configuration and secrets | Runtime configuration, environment variable, credential, key, or policy change | Name owner, default, precedence, environment scope, and schema/parse validation. Never place a secret in source, logs, evidence, or ordinary identifiers. | Review access boundary, rotation/expiry, rollout and rollback, and validate deployed configuration through existing secret/configuration controls. | Configuration validation, redacted diff, existing secret scan or CI result, access/rotation review, or residual risk. |
| Dependency and supply chain | Add, update, remove, or materially configure a runtime/build dependency | Record necessity, existing alternative, lockfile impact, maintained status, license/security signal when available, and removal condition. | Review transitive impact, compatibility, known vulnerability/advisory evidence, upgrade/rollback path, and ownership; independently review privileged or high-blast-radius dependencies. | Manifest/lockfile diff, existing dependency/security scan or CI output, compatibility test, and removal plan. |
| Documentation and operational knowledge | Non-obvious decision, public behavior, migration, incident fix, or high-risk operation | Update the closest API, configuration, or operator documentation and link a regression test or verification record. | Record an ADR for non-obvious irreversible choices; provide a runbook with diagnosis, recovery, ownership, and rollback for high-risk operations. | Documentation/ADR/runbook path, API change note, regression test, review, or drill output. |
| Reproducible development | New service/tooling, onboarding friction, CI-only defect, or environment-sensitive behavior | Record the current start, check, and test commands plus required non-secret configuration and tool-version constraints. | Reproduce the critical path in a clean worktree, container, or existing CI environment with minimal test data; document unavailable external prerequisites and residual risk. | Setup/check/test output, version manifest, minimal-data fixture, CI run, or clean-environment record. |

Do not create an empty branch, PR, release, migration, scan, runbook, or commit merely to claim compliance. A commit is an atomic unit of reviewed intent, not a snapshot after every keystroke. If a repository or user owns commit, PR, or release execution, prepare the evidence and handoff without performing an unauthorized external action.

## Compound Level 2 Gate

Activate this gate only for a Level 2 request that combines an unclear failure or regression with three or more triggered delivery rows, or combines money/public-contract work with migration, release, secret, or dependency change. Level 0 never activates it; a normal Level 1 change uses only its directly triggered rows.

Before implementation, list every triggered row as `mitigate now`, `stage separately`, or `block pending evidence`; give each one its owner, evidence, and rollback or removal condition. Do not let a same-day mitigation become permission to collapse an API change, backfill, credential rotation, dependency upgrade, and release into one PR.

For an ambiguous remote write, preserve pending state and reconcile before retrying. For a public migration, expand compatibly, audit consumers, backfill under measurable stop conditions, and contract only after recovery evidence. For rollout, deploy with the flag disabled, stage exposure, monitor a named window, and disable the flag before reverting code. For secrets, record redaction, owner/access boundary, rotation/expiry, and rollback without reproducing values. For dependencies, record advisory, lockfile/transitive impact, compatibility, rollback, and removal. For CI and Git, exclude unrelated dirty changes, use green required checks, and reject force-merge or bypass. For operations, record ADR/runbook/recovery owner and a local non-secret fixture path before declaring the compound change ready.

Before returning a compound Level 2 plan or evidence ledger, run a coverage preflight. State the Level 2 classification and a concrete `mitigate now`, `stage separately`, or `block pending evidence` decision for every triggered row. Confirm explicitly that an incident timeout remains a durable pending unknown until reconciled and is retried only after definitive absence or a retryable pre-acceptance rejection; every public migration uses `Expand-Migrate-Contract`, names consumers, and states a measurable backfill stop signal; the existing feature flag starts disabled, has staged exposure and a named monitoring window, and can be disabled before code rollback; required CI is green and neither bypass nor force-merge is allowed; unrelated dirty work is excluded; secret rotation names redaction plus an access or expiry control; and non-secret local reproduction plus an ADR/runbook and recovery owner are recorded. State that no production action occurs without authorization. Do not rely on a related paragraph elsewhere in the response to imply any of these decisions. A phrase such as `measurable stop signal`, `local path`, or `force-merge blocked` is not enough by itself: name a backfill metric and threshold or block that migration pending the owner-approved bound; name a non-secret fixture plus a clean worktree, container, or CI reproduction and the existing start/check/test tool surfaces to discover; and explicitly reject force-merge of red CI. In the returned ledger, include standalone `Operational knowledge:` and `Reproducibility:` lines that name the ADR/runbook/recovery owner and the fixture/clean environment/tool-discovery status; do not rely on implicit mentions elsewhere.

For a concise compound response, emit this minimum checklist before adding detail. Each line is a decision or an explicit blocker, not a suggestion:

```text
Change level: 2
Causal status: symptom, hypotheses, discriminating check, and `Causal conclusion: unknown` when the intervention is unrun
Remote write: durable `pending`; reconcile the canonical identity; retry only after definitive absence or retryable pre-acceptance rejection
Migration: `Expand-Migrate-Contract`; named consumers; backfill stop condition with a concrete metric and threshold (for example replication lag, queue age, or error rate), or block pending an owner-approved bound
Release: feature flag disabled by default; staged rollout; monitoring window; disable the flag first before code rollback
CI/Git: required CI must be green; bypass is not allowed; do not force-merge red CI; exclude unrelated dirty worktree changes
Secrets: rotate and redact; name the owner plus access or expiry control
Supply chain: advisory/vulnerability, lockfile, compatibility, rollback, and removal decision
Operational knowledge: ADR/runbook with diagnosis, recovery, rollback, and owner
Reproducibility: non-secret fixture plus clean worktree/container/CI; discover and reuse existing repository tools and start/check/test commands
Authority: no production action without explicit authorization
Verification: exact command and observed result, or `not run`/`blocked` with the reason
```

If a row is irrelevant, write `not applicable` with a reason; do not silently omit it. This checklist is a compression aid for compound responses, not a substitute for the detailed ledger or executed verification.

## Evidence-Based AI Collaboration

- Separate observed facts, project constraints, hypotheses, and proposed changes. Read the owner, callers, tests, configuration, and runtime evidence before editing; do not promote generated explanation into a fact.
- Convert vague requests into observable acceptance criteria and bounded tradeoffs. Escalate only when a missing choice materially changes authority, compatibility, data handling, or irreversible behavior.
- Change one coherent behavior at a time, verify it, and preserve a rollback path. Use a second independent perspective to attack assumptions, failure paths, ownership, compatibility, security, and performance rather than to repeat the first plan.
- Leave a concise decision record in the ledger for non-obvious tradeoffs, rejected alternatives, and deletion conditions. When evidence cannot distinguish explanations, report unknown and add instrumentation, a reproducer, or a reversible guard.

## Explainable Implementation and Chinese Maintenance Notes

Apply this section to Level 1 and Level 2 code changes unless the repository requires another documentation language. Explain behavior first through focused module boundaries, explicit types, stable names, narrow functions, and visible error/state transitions. Do not use comments to compensate for unclear control flow, hidden mutation, or overloaded abstractions.

Add concise Chinese comments where a competent maintainer cannot infer the **why**, constraint, ownership rule, or failure semantics from the code alone. Typical triggers are a non-obvious invariant, state transition, causal-owner repair, compatibility branch, concurrency/order rule, security boundary, external-service ambiguity, resource-complexity choice, or intentionally retained workaround. Write the comment immediately above the decision it explains; state the reason and consequence, not a mechanical translation of the next line. Keep identifiers, public API names, and language required by the repository unchanged.

Do not add line-by-line narration, stale comments, duplicated prose, unsupported claims, personal data, secrets, or comments that conceal a known uncertainty. Delete or revise a comment whenever its decision changes. For Level 2, review changed explanatory comments against the corresponding invariant, test, ledger, and runtime evidence; record `Explainability: <comments added/updated or not applicable; review result>` in the final report. For Level 1, record the same line when an explanation-triggered decision was changed.

## Implementation, Tests, and Review

State the behavioral invariant before implementation. Validate input, authorization, resource ownership, state transitions, and payload limits at system boundaries. Never swallow errors: classify them, return or raise a safe error, and log enough context to investigate.

Use existing project utilities and patterns. Add an abstraction only when it removes meaningful duplication or matches an established local convention.

- For an applicable structural change, test the behavior at the public or module boundary rather than its private decomposition. Cover the expected error outcome and any cross-boundary state transition; add a contract test for a public extension point or multiple adapters.
- For a bug fix, add or strengthen a regression test before declaring the fix complete. Do not call it a root-cause fix unless the reported failure is reproduced or causally linked to the changed behavior; otherwise report it as mitigation and state the residual risk.
- For a behavior change with an existing test surface, write or update the test before or alongside implementation; include important failure behavior.
- When a task supplies a runtime, latency, memory, call-count, or cost budget, treat a passing public example as necessary but insufficient. Inspect the largest visible input and the stated contract, estimate the changed path's worst-case complexity or resource use, and run a deterministic boundary probe within the declared contract. If the contract has no safe upper bound, record that uncertainty and do not claim the budget is verified; hidden scale remains a residual risk.
- For a behavior-preserving refactor without protection, add regression coverage before restructuring.
- For a Level 2 change, perform an independent review pass after implementation. Read the diff and acceptance criteria as a fresh reviewer; use a separate reviewer or agent when available. Check correctness, security, compatibility, cleanup, and test adequacy.

## Safeguard Matrix

Apply the relevant row; explain a deliberate omission in the evidence ledger.

| Situation | Required default |
|---|---|
| Every externally handled service request | Emit structured logs with timestamp, level, service, environment, version, operation, `traceId`, duration, and outcome. |
| Cross-service or asynchronous flow | Propagate `traceId`; use `spanId` for a dependency call and `correlationId` across request boundaries. |
| Mutable business or personal data | Identify the authoritative owner, valid state transitions, retention/deletion boundary, authorization boundary, and redaction requirements. Do not create an unmanaged duplicate source of truth. |
| API, event, shared-library, or configuration boundary | Validate input shape, size, range, authorization, and ownership. Return a stable error code and safe message; document consumers, compatibility/default behavior, migration, and rollback before a breaking change. |
| External network, database, cache, or SDK call | Set an explicit timeout and cancellation behavior; propagate a deadline where supported; classify safe retry, terminal failure, and unknown outcome; log dependency and latency without secrets. |
| Retryable remote operation | Retry only transient, idempotent work; bound attempts; use exponential backoff with jitter. |
| Ambiguous remote write or expired idempotency window | Persist pending state before the call; reconcile by canonical operation identity as confirmed, absent, or unknown; resend only after definitive absence or retryable pre-acceptance rejection. Persist terminal rejection and safe reason as failed, then acknowledge or dead-letter; no later path may revive or alter it. Re-verify canonical identity before provider confirmation, acknowledgement, dead-letter, and recovery handoff. Test provider acceptance before timeout or crash, unavailable reconciliation, identity mismatch at every finalization boundary, acknowledgement failure after durable confirmation, retryable versus terminal rejection, concurrent recovery-job deduplication and handoff, and structured retry-decision audit output. |
| New or restructured business module | Name its owner and input/output contract; make mutation and I/O explicit; keep domain policy independent from transport and storage where practical; review changed dependency direction and private-state access. |
| New extension point or public contract | Keep the existing path direct unless there are two independent consumers, a stable external contract, or a demonstrated testing boundary. For a real extension seam, document consumers, compatibility/versioning, and a contract or integration test. |
| Multi-resource state transition | Use one transaction when available. Otherwise define durable ordering, idempotency, recovery ownership, and compensation or outbox behavior; test an interruption between resources. |
| Create, update, charge, send, or enqueue action | Guarantee idempotency with a key, uniqueness constraint, or equivalent; define consistency with a transaction or explicit design. |
| Critical rule, public contract, or broad input domain | Test representative success and failure cases plus invariants, compatibility, boundary values, and property/table-driven cases where appropriate. Keep time, randomness, concurrency, and external I/O deterministic. |
| Expensive or exposed operation | Establish a latency, throughput, error, resource, call-count, or cost budget; measure a baseline and result. Apply pagination, payload limits, rate limits, concurrency limits, cancellation, and backpressure as applicable. |
| Optional or failing dependency | Choose and test a failure mode: fallback, partial response, queued retry, or clear failure; use circuit breaking when available. |
| Sensitive or privileged operation | Review the trust boundary, server-side authentication and authorization, tenant/resource ownership, input validation, abuse path, secret handling, auditability, and sensitive-data redaction. |
| Deployable service | Provide health/readiness checks, request/error/latency metrics, low-cardinality labels, actionable alerts with an owner and response, and environment-specific configuration. |
| Schema or API evolution | Identify consumers; use versioned migrations and backward-compatible additions; establish rollback before production data changes; add migration, consumer-contract, and compatibility coverage. |
| Level 1 or Level 2 Git-tracked change | Keep one atomic, verified change scope; inspect the final diff; do not commit secrets or unrelated edits. Use the repository's commit and PR workflow. |
| Shared-repository merge | State PR scope, acceptance criteria, risk, rollback, and verification. Treat required CI as a merge minimum; record an approved exception with scope and expiry rather than bypassing it. |
| Release, feature rollout, or operational configuration | Define the release owner, observable outcome, monitoring window, stop condition, rollback mechanism, and recovery owner; rehearse recovery when impact warrants it. |
| Schema, backfill, or persistence-format migration | Use compatible expansion before migration and later contraction; retain consumer, dry-run, recovery, and backup/restore evidence for destructive work. |
| Configuration, environment variable, or secret | Define owner/default/precedence/schema and environment scope; redact values and review access, rotation, expiry, rollout, and rollback as applicable. |
| Added or materially changed dependency | Record necessity, existing alternative, lockfile/transitive impact, maintenance, license/security signal, compatibility coverage, and removal condition. |
| Non-obvious or high-risk operation | Update nearest documentation; add an ADR or operator runbook when the choice is irreversible, public, or requires diagnosis/recovery. |
| Environment-sensitive or onboarding-critical workflow | Record start/check/test commands, non-secret setup, tool versions, and clean-environment or CI reproduction evidence for Level 2. |

`traceId` links one incoming request's full lifecycle. It is not a business ID and must not contain personal or secret data. Prefer structured logs; never log credentials, access tokens, session identifiers, full payment data, or unnecessary personal data.

## Cleanup Audit

Inspect the final diff and search specifically for leftovers created or superseded by the change:

- unused files, imports, exports, symbols, dependencies, and type declarations;
- obsolete handlers, components, routes, jobs, queues, event names, and API clients;
- stale feature flags, configuration keys, environment variables, documentation, examples, and telemetry labels;
- duplicate implementations or changed contracts without matching callers, tests, error handling, or migrations.
- new dependency cycles, reverse-layer imports, shared mutable globals, reach-through access to private module state, catch-all utility modules, and domain decisions embedded in transport or persistence adapters.

Delete confirmed leftovers. For a potentially dynamic reference, inspect its runtime registration before retaining or deleting it. Do not perform unrelated cleanup in a feature task.

## Enforcement Bridge

First discover the repository's existing hooks, CI, linting, type checks, tests, and static-analysis tools. Use them; do not add a new dependency merely because it appears in a recommendation.

When the user asks to make this policy mechanically enforceable, read [references/enforcement.md](references/enforcement.md). For a target repository, copy [scripts/validate_evidence.py](scripts/validate_evidence.py) and [scripts/check_change_evidence.py](scripts/check_change_evidence.py) into `.adam/scripts/`; the GitHub Actions template expects that layout. Use those copied scripts as the standard-library evidence gate, enable both `--require-for-code-change` and `--require-level-two-for-high-risk`, wire the same required checks into local hooks and CI, and never bypass or weaken a failing quality gate. The high-risk path classifier is a conservative floor for obvious authentication, authorization, payment, migration, schema, secret, deployment, infrastructure, queue, and worker paths; it does not replace semantic review and a harmless filename never justifies downgrading risky behavior.

## Verification Protocol

1. Run `git diff --check` when the workspace is a Git repository.
2. Run the repository's relevant formatter, lint, type check, tests, build, and static-analysis commands. Prefer narrow checks first, then required project-wide checks.
3. Verify every acceptance criterion, including applicable failure, retry, concurrent-write, migration, and compatibility behavior.
4. Re-read the final diff and ledger. Confirm that no active old path remains and every listed verification result is actual.
5. If an applicable check is unavailable, state why, what was run instead, and the residual risk. Do not call the task fully verified.

When CI exists, use its required checks as the minimum bar and do not weaken or bypass them. Keep local verification and CI requirements aligned.

## Self-Application and Package Maintenance

This policy applies to its own package. Treat `SKILL.md`, its user-facing metadata, root validator scripts, tests, templates, references, README, and active CI workflow as one implementation surface. `SKILL.md` is the normative source; README summaries must not introduce a conflicting requirement.

For every change to this package:

1. Classify policy, schema, validator, template, workflow, or automation changes as at least Level 1; use Level 2 for changes to the public contract or the package's enforcement architecture.
2. Keep one unique evidence artifact per logical change under `.adam/evidence/`; update it only while continuing the same change.
3. Update every affected source, template, reference, README summary, test, and CI command in the same change. Delete replaced instructions, stale paths, obsolete examples, and duplicated enforcement logic.
4. Keep the root `scripts/` files as this package's canonical implementation. Target repositories copy them into `.adam/scripts/`; do not maintain a second package-local implementation.
5. Run the evidence-script tests after validator or gate changes, parse every JSON/YAML artifact changed, validate the Skill package, and verify the active workflow references real paths.
6. Treat the Git default branch at its verified commit and passing required checks as the current state. Do not publish manually maintained version, date, or status claims that cannot be verified from Git or CI.
7. For a Level 2 package update that changes three or more of causal diagnosis, design boundaries, data/contracts, operational readiness, delivery lifecycle, or evidence enforcement, run a composite forward test in a fresh context. Give the test agent an explicit allowed-input boundary of the raw request and Skill, keep the scoring rubric separate, include deliberate unsafe mutations in the deterministic evaluator, and record the prompt, declared boundary, input/scorer hashes, score, and limitations. Call this protocol-isolated unless an external sandbox proves stronger isolation. When a package claim says the causal process rejects shallow repairs or locates a causal owner, also run a feasible pinned external regression replay: verify input-source hashes, test the original defect, the official correction, and at least one deliberately incomplete near-miss against a separate hidden contract. Keep that replay offline after source materialization, and distinguish protocol effectiveness from any claim about aggregate model capability. If a package claim says the Skill improves repair success or causal-analysis quality, additionally use the preregistered paired protocol in `references/effect-evaluation.md`; do not make the claim until its completed analysis reports `improved`. If no safe reproducible external replay or effect experiment is available, record the constraint and do not make a general effectiveness claim.

## Adam's Project Overrides

Add concise, testable project-specific rules here in English. These rules refine the generic workflow unless they conflict with stricter repository or platform requirements.

- Prefer deletion over parallel replacement paths.
- Require a feature flag and rollback path for changes that alter a core user workflow.
- Treat logs, configuration, documentation, routes, tests, and telemetry as part of a feature's implementation surface.

## Final Report Format

Use this exact shape for Level 1 and Level 2 changes:

```text
Change level: ...
Canonical owner: ...
Acceptance criteria: ...
Changed: ...
Removed or retained compatibility: ...
Safeguards: ...
Quality decisions: <design/dependency/extension; ownership/lifecycle; error/retry; contract; operational budget; threat boundary, or not applicable>
Delivery decisions: <Git/PR; release/recovery; migration; configuration/secrets; supply chain; operational knowledge; reproducibility, or not applicable>
Explainability: <comments added/updated or not applicable; review result>
Cleanup audit: <scoped retirement sweep; removed paths, retained consumers/removal conditions, unresolved unknowns, and evidence>
Documentation synchronization: <docs/comments/examples/version/metadata updated, deleted, or confirmed current; evidence>
Instrumentation: <not applicable, or event boundaries/schema, redaction/cardinality review, tests and runtime/development evidence>
Verified: <command> - <result>
Independent review: <result or not required>
Evidence artifact: <path or enforcement mode not enabled>
Remaining risks: ...
Causal conclusion: <not activated | root-cause fix | mitigation | instrumentation-only | unknown>
```

Keep the report concise, factual, and based on executed work.
