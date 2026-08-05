Change level: Level 2 compound: money + ambiguous provider timeout + public API/schema migration + release, secret, dependency, CI/Git, and reproducibility rows. No file edits, production actions, credential actions, merges, or deployments occur without explicit authorization.

Observations:
- Duplicate settlement effects are observed after provider timeouts; no trace, reproduction, or causal path is confirmed.
- Provider timeout may mean accepted, absent, or unknown remote state.
- `settlement_status` has unknown dashboard, event, and external partner consumers.
- CI, migrations, dashboards, secrets manager, dependency scanner, and feature flags exist, but concrete commands are unknown.
- Worktree contains unrelated documentation from another developer.
- No production credential, deployment permission, or CI exception exists.
- Local validation must work without production credentials.

Hypotheses:
- Primary: timeout handling retries an operation whose provider result is unknown, causing duplicate settlement effects.
- Alternative: duplicate effects come from webhook redelivery, recovery jobs, queue ack ordering, or identity mismatch at finalization.
- Causal conclusion now: unknown. Treat any immediate retry-every-time change as unsafe until reconciliation evidence exists.

Compound Level 2 coverage preflight:
- Ambiguous incident timeout: mitigate now. Owner: payment settlement/reconciliation owner once identified. Evidence: traces, idempotency identity, timeout/recovery reproduction. Decision: durable pending unknown until reconciled; retry only after definitive absence or retryable pre-acceptance rejection.
- Public API/schema rename: stage separately. Owner: partner API/schema owner. Evidence: consumer audit across partners, dashboards, events, dynamic lookups. Decision: Expand-Migrate-Contract; keep `settlement_status`, add compatible `settlement_state`, name consumers, and define measurable backfill stop signal, such as audited row count plus reader/writer parity and error budget.
- Feature flag/release: stage separately. Owner: release owner. Evidence: flag config and staged metrics. Decision: existing feature flag is retained, starts disabled, has staged exposure and a named monitoring window, and can be disabled before code rollback.
- Atomic Git/PR/CI: block pending evidence. Owner: change author/release manager. Evidence: clean scoped diff and required CI. Decision: required CI must be green; bypass and force-merge are rejected; unrelated dirty documentation is excluded.
- Secret rotation: block pending authorization. Owner: credential owner/security. Evidence: redacted rotation record, access boundary, expiry or rotation control, rollback path. Secret values must not appear in code, logs, evidence, or tickets.
- Dependency upgrade: stage separately unless the advisory is actively exploitable in this path. Owner: dependency owner/security. Evidence: advisory, lockfile/transitive impact, compatibility result, rollback/removal plan.
- Operational knowledge: mitigate now for incident runbook, stage ADR for migration/API choices. Owner: payments on-call/API owner. Evidence: ADR/runbook with recovery owner.
- Reproducible development: mitigate now. Owner: platform/payments owner. Evidence: non-secret local fixture and documented start/check/test commands discovered from repo, not invented.

Plan:
1. Freeze scope: same-day incident mitigation only. Reject retry-all-timeouts, column deletion, flag deletion, force-merge, direct production promotion, and committing unrelated work.
2. Identify canonical owners before edits: charge creation, provider timeout handling, settlement finalization, webhook/recovery processing, idempotency key generation, queue ack/dead-letter paths, API serializers, migrations, flags, dependency manifests, and CI gates.
3. Add/verify the invariant: one canonical operation identity per settlement effect, including business event plus tenant, recipient/resource, amount, payload version/content hash, and provider operation identity where available.
4. Implement only after evidence: timeout after possible provider acceptance records durable `pending_reconciliation`; recovery reconciles by canonical identity; confirmed maps to settled once; definitively absent may retry with bounded idempotent policy; unknown remains pending with owned recovery.
5. Test failure paths before release: provider accepted-before-timeout, unavailable reconciliation, identity mismatch at confirmation/ack/dead-letter/recovery handoff, terminal rejection, ack failure after durable confirmation, concurrent recovery deduplication, and structured retry-decision audit logs.
6. Stage API migration separately: add `settlement_state` as compatible expansion, keep `settlement_status`, update docs/contracts, backfill 40M rows under stop conditions and rollback, switch consumers after evidence, delete old column only in later contraction.
7. Stage secret rotation and SDK upgrade as separate reviewed changes unless incident evidence proves they are the causal owner.
8. Release only via normal PR after scoped diff review, green required CI, independent Level 2 review, flag-disabled deploy, staged exposure, monitoring window, rollback drill or documented residual risk.

Evidence ledger:
- Canonical owner: unknown pending repository inspection.
- Affected callers/contracts: payment provider calls, settlement state owner, webhooks/recovery jobs, partner API, dashboards/events, migrations, feature flag, CI/release.
- Acceptance criteria: no duplicate settlement effects across timeout/recovery; unknown remote writes stay pending; public API remains backward compatible; migration is reversible; secrets redacted; dependency change verified; CI green; local non-secret reproduction documented.
- Replaced paths: none until canonical old retry/finalization paths are proven and migrated.
- Retained compatibility: `settlement_status` retained for named consumers until contract evidence permits removal.
- Safeguards: idempotency, three-state reconciliation, structured redacted logs with trace/correlation IDs, bounded retries, durable recovery ownership, consumer-contract tests, migration dry run, flag rollback, secret access/expiry control.
- Verification: not run by constraint; concrete commands must be discovered from repository CI/config before implementation.
- Independent review: required before merge/release.
- Evidence artifact: conversational ledger only unless repository opts into machine evidence.
- Remaining risks: causal owner unproven, consumer set unknown, production authority absent.
