**Observations**

- Duplicate settlement effects occur after provider timeouts, but no trace, reproduction, or causal path is confirmed.
- Provider timeout is an ambiguous remote-write outcome: the provider may have accepted the charge.
- `settlement_status` has unknown dashboard, event, and partner API consumers.
- CI, migrations, dashboards, secrets manager, dependency scanner, and feature flags exist, but concrete commands/config are unknown.
- No production credential, deployment permission, CI exception, or authority to include unrelated dirty docs exists.

**Hypotheses**

- Primary: retries after timeout are treating `UNKNOWN` remote-write outcomes as safe retryable failures.
- Alternative: canonical idempotency identity is incomplete or mismatched at confirmation/finalization boundaries.
- Alternative: duplicate settlement is caused downstream by recovery, acknowledgement, event, or dashboard sync behavior rather than charge retry itself.

**Plan**

1. **Mitigate now:** stop blind timeout retries. Persist timeout outcomes as durable `pending_unknown`, reconcile by canonical operation identity, and resend only after `ABSENT` or retryable pre-acceptance rejection.
2. **Mitigate now:** add/verify trace, correlation, idempotency identity, retry-decision, provider-result, acknowledgement, and recovery-handoff logging without payloads or secrets.
3. **Stage separately:** public API rename. Use Expand-Migrate-Contract: add `settlement_state` compatibly while retaining `settlement_status`; audit dashboard, event, and partner consumers before contraction.
4. **Stage separately:** 40M-row backfill. Block destructive migration until owner approves a measurable stop signal, for example `100% rows with settlement_state populated, 0 mismatches in sampled reconciliation, backfill error rate below approved threshold`.
5. **Block pending evidence:** deleting the old column and deleting the existing feature flag in the same release. The flag must start disabled, support staged exposure, use a named monitoring window, and be disable-able before code rollback.
6. **Stage separately:** webhook credential rotation through secrets manager only, with redacted evidence, named owner/access boundary, expiry or rotation control, and rollback.
7. **Stage separately:** vulnerable transitive SDK upgrade after dependency scanner evidence, lockfile/transitive impact review, compatibility tests, and rollback plan.
8. **Block:** force-merge with red CI, unrelated dirty documentation, and direct production promotion. Required CI must be green; bypass/force-merge is rejected; unrelated dirty work is excluded. No production action occurs without authorization.

**Evidence Ledger**

Change level: 2, compound gate active.

Canonical owner: unknown until repository owner paths are inspected; candidate owner is the payment timeout/retry/reconciliation state transition.

Acceptance criteria: no duplicate settlement after provider timeout; timeout remains durable pending unknown until reconciled; retry only after definitive absence or retryable pre-acceptance rejection; identity mismatch cannot finalize; partner API remains backward compatible; CI green before merge.

Causal diagnosis: Causal Full active. Symptom is duplicate settlement after provider timeout. Candidate path: provider timeout -> local retry decision/state owner -> duplicate charge or settlement side effect -> duplicate settlement. Counterfactual proposed: classify timeout as `UNKNOWN`, persist pending, reconcile by canonical identity before resend. Actual result: unrun/read-only, so unknown.

Safeguards: idempotency identity includes business event plus tenant, recipient/resource, amount, payload version/content hash; test `FOUND`, `ABSENT`, `UNKNOWN`, terminal rejection, retryable pre-acceptance rejection, identity mismatch, concurrent recovery dedupe, and acknowledgement failure.

Contract evolution: public migration must use Expand-Migrate-Contract; consumers include partner API, dashboards, and events; contraction is blocked until consumer audit and compatibility evidence exist.

Delivery decisions: Git/PR is one atomic scoped change excluding unrelated docs; release uses disabled feature flag, staged exposure, named monitoring window, stop condition, and rollback by disabling flag before reverting code; CI red force-merge blocked.

Configuration and secrets: rotate webhook credential only via secrets manager; redact values; record owner, access boundary, expiry/rotation, rollout, and rollback.

Supply chain: SDK upgrade staged separately with dependency scanner/advisory evidence, lockfile impact, compatibility tests, rollback, and removal/upgrade rationale.

Operational knowledge: create ADR/runbook covering timeout reconciliation, duplicate-settlement diagnosis, recovery owner, rollback, and incident response.

Reproducibility: new developer validation requires non-secret local fixture plus clean worktree/container/CI reproduction; existing start/check/test commands must be discovered before implementation and not guessed.

Verified: read-only planning only; no repository commands, edits, production actions, CI bypass, secret access, or deployment performed.

Remaining risks: root cause unconfirmed; unknown dynamic consumers; migration size and backfill bounds not approved; no concrete local command surface discovered.

Causal conclusion: unknown
