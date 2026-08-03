---
name: adam-development-habits
description: Enforce Adam's risk-scaled development habits for AI-assisted feature work, bug fixes, refactors, integrations, and reviews. Use proactively whenever editing code to define project principles and acceptance criteria, identify the canonical implementation, remove stale paths, apply relevant resilience safeguards, and provide executed verification evidence before completion.
---

# Adam's Development Habits

Apply this workflow to every code change. Follow stricter repository instructions first. Keep changes focused and reversible. Do not add dependencies, abstractions, compatibility layers, or unrelated refactors without a concrete requirement.

## Operating Model

This skill is the policy layer, not a replacement for tests, static analysis, hooks, or CI. Use it to make the AI's reasoning and evidence explicit; use project tooling to enforce what can be automated.

Apply the lightest level that preserves confidence:

| Level | Scope | Required evidence |
|---|---|---|
| 0 | Documentation, comments, formatting, or an obvious one-line correction with no behavior change. | Inspect the diff and run the relevant narrow check. |
| 1 | Normal feature, bug fix, refactor, integration, or configuration behavior change. | Acceptance criteria, evidence ledger, relevant tests/checks, and cleanup audit. |
| 2 | Public API, schema migration, authentication, money, privacy, concurrency, cross-service flow, architectural change, or broad refactor. | Level 1 plus a concise plan, rollback/compatibility strategy, failure-path tests, and an independent review pass. |

Do not downgrade a change to avoid evidence. If uncertain, use the higher level.

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
- every replaced path was removed, or each retained path has a real consumer, removal condition, and coverage;
- relevant safeguards were implemented or explicitly shown to be not applicable;
- the exact verification commands were run and their outcome was read;
- the final report records changed files, removed code, verification evidence, and remaining risks.

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
Safeguards: <applicable items from the matrix>
Verification: <commands run and actual results>
```

Use narrow searches to establish the ledger. Check imports, exports, registrations, routes, configuration keys, message names, tests, and dynamic lookup conventions. Never infer that code is dead only because a direct reference search is empty.

## Evidence Enforcement Mode

Use the conversational ledger by default. A repository opts into machine-enforced evidence only when it contains an `.adam/` directory or the user explicitly requests enforcement.

For an opted-in repository, create one `.adam/evidence/<change-id>.json` artifact for every Level 1 or Level 2 change. Start from [assets/evidence-ledger.example.json](assets/evidence-ledger.example.json), then validate it with the project-local evidence script before completion. Keep the artifact in the same pull request as the code change.

The artifact records facts after verification; it does not replace tests or let a failed command become passing by declaration. For a Level 2 change, include rollback or compatibility strategy and an independent review outcome.

## One Active Implementation

1. Locate the existing owner of the behavior before adding code.
2. Modify the canonical owner in place when possible.
3. When replacing behavior, move every caller, then delete the old implementation and its references in the same change.
4. Remove obsolete tests, types, routes, jobs, queue consumers, configuration, feature flags, documentation, examples, and telemetry labels.
5. Preserve an old path only for a verified external compatibility or controlled rollout requirement. Record its consumer and deletion condition in the ledger.

Do not leave commented-out code, duplicate business rules, unused helpers, unused imports or exports, abandoned feature flags, dead endpoints, speculative abstractions, or two implementations that claim the same responsibility.

## Implementation, Tests, and Review

State the behavioral invariant before implementation. Validate input, authorization, resource ownership, state transitions, and payload limits at system boundaries. Never swallow errors: classify them, return or raise a safe error, and log enough context to investigate.

Use existing project utilities and patterns. Add an abstraction only when it removes meaningful duplication or matches an established local convention.

- For a bug fix, add or strengthen a regression test before declaring the fix complete.
- For a behavior change with an existing test surface, write or update the test before or alongside implementation; include important failure behavior.
- For a behavior-preserving refactor without protection, add regression coverage before restructuring.
- For a Level 2 change, perform an independent review pass after implementation. Read the diff and acceptance criteria as a fresh reviewer; use a separate reviewer or agent when available. Check correctness, security, compatibility, cleanup, and test adequacy.

## Safeguard Matrix

Apply the relevant row; explain a deliberate omission in the evidence ledger.

| Situation | Required default |
|---|---|
| Every externally handled service request | Emit structured logs with timestamp, level, service, environment, version, operation, `traceId`, duration, and outcome. |
| Cross-service or asynchronous flow | Propagate `traceId`; use `spanId` for a dependency call and `correlationId` across request boundaries. |
| API or public boundary | Validate input shape, size, range, authorization, and ownership. Return a stable error code and safe message. |
| External network, database, cache, or SDK call | Set an explicit timeout; propagate a deadline where supported; log dependency and latency without secrets. |
| Retryable remote operation | Retry only transient, idempotent work; bound attempts; use exponential backoff with jitter. |
| Create, update, charge, send, or enqueue action | Guarantee idempotency with a key, uniqueness constraint, or equivalent; define consistency with a transaction or explicit design. |
| Expensive or exposed operation | Apply pagination, payload limits, rate limits, concurrency limits, and backpressure as applicable. |
| Optional or failing dependency | Choose and test a failure mode: fallback, partial response, queued retry, or clear failure; use circuit breaking when available. |
| Sensitive or privileged operation | Authenticate, authorize server-side, audit the action, and redact secrets and unnecessary personal data. |
| Deployable service | Provide health/readiness checks, request/error/latency metrics, and environment-specific configuration. |
| Schema or API evolution | Use versioned migrations and backward-compatible additions; establish rollback before production data changes. |

`traceId` links one incoming request's full lifecycle. It is not a business ID and must not contain personal or secret data. Prefer structured logs; never log credentials, access tokens, session identifiers, full payment data, or unnecessary personal data.

## Cleanup Audit

Inspect the final diff and search specifically for leftovers created or superseded by the change:

- unused files, imports, exports, symbols, dependencies, and type declarations;
- obsolete handlers, components, routes, jobs, queues, event names, and API clients;
- stale feature flags, configuration keys, environment variables, documentation, examples, and telemetry labels;
- duplicate implementations or changed contracts without matching callers, tests, error handling, or migrations.

Delete confirmed leftovers. For a potentially dynamic reference, inspect its runtime registration before retaining or deleting it. Do not perform unrelated cleanup in a feature task.

## Enforcement Bridge

First discover the repository's existing hooks, CI, linting, type checks, tests, and static-analysis tools. Use them; do not add a new dependency merely because it appears in a recommendation.

When the user asks to make this policy mechanically enforceable, read [references/enforcement.md](references/enforcement.md). Select the smallest compatible toolchain, use [scripts/validate_evidence.py](scripts/validate_evidence.py) and [scripts/check_change_evidence.py](scripts/check_change_evidence.py) as the standard-library evidence gate, wire the same required checks into local hooks and CI, and never bypass or weaken a failing quality gate.

## Verification Protocol

1. Run `git diff --check` when the workspace is a Git repository.
2. Run the repository's relevant formatter, lint, type check, tests, build, and static-analysis commands. Prefer narrow checks first, then required project-wide checks.
3. Verify every acceptance criterion, including applicable failure, retry, concurrent-write, migration, and compatibility behavior.
4. Re-read the final diff and ledger. Confirm that no active old path remains and every listed verification result is actual.
5. If an applicable check is unavailable, state why, what was run instead, and the residual risk. Do not call the task fully verified.

When CI exists, use its required checks as the minimum bar and do not weaken or bypass them. Keep local verification and CI requirements aligned.

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
Verified: <command> - <result>
Independent review: <result or not required>
Evidence artifact: <path or enforcement mode not enabled>
Remaining risks: ...
```

Keep the report concise, factual, and based on executed work.
