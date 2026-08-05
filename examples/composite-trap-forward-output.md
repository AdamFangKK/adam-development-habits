**Observations**
- Duplicate settlement effects are observed after provider timeouts, but no trace, reproduction, or confirmed causal path exists.
- Provider timeout is ambiguous: the charge may already have been accepted remotely.
- `settlement_status` is a public/consumer-facing contract with unknown dashboard, event, and partner usage.
- Existing CI, migrations, dashboards, secrets manager, dependency scanner, and feature flags exist, but exact commands are unknown.
- Worktree has unrelated documentation by another developer.
- No authority exists for production deploy, credential rotation, CI override, or force merge.

**Hypotheses**
- Primary: duplicate effects come from retrying timeout results as if they were definitively absent.
- Alternative: duplicates may come from weak idempotency identity, recovery job races, webhook replay, settlement finalization mismatch, or provider reconciliation identity mismatch.
- Discriminating evidence needed: traces/logs around timeout, provider acceptance/reconciliation records, idempotency keys, queue/job retries, webhook deliveries, and settlement state transitions.

**[The 3 Ways This Dies]**
1. Retrying timed-out charges creates real duplicate settlements.
   Defense: treat remote timeout as `unknown`, persist pending state, reconcile by canonical operation identity, retry only after definitive absence or retryable pre-acceptance rejection.
2. Renaming and deleting `settlement_status` breaks partners, dashboards, and events.
   Defense: expand-migrate-contract: add compatible `settlement_state`, dual-read/write or alias, consumer audit, staged removal only after evidence.
3. Bundling migration, SDK upgrade, secret rotation, feature-flag deletion, CI override, and production deploy hides failure cause.
   Defense: split into atomic changes; no force merge; no production action without authorization and green checks.

**[The Trilemma]**
- A, safest: freeze risky retries, add pending/reconciliation semantics, keep API compatibility, split migration/SDK/secret/deploy into separate reviewed releases.
- B, same-day mitigation: disable or gate timeout retries, preserve pending records, add reconciliation job/monitoring using existing mechanisms, ship no schema deletion.
- C, counterintuitive: stop settling synchronously after provider timeout and move all ambiguous settlements to an operator-visible reconciliation queue until identity-safe automation is proven.

Recommended path: B today, then A as the durable fix. Reject direct production promotion, force merge, dirty-worktree commit, old-column deletion, and unauthorized credential rotation.

**Plan**
1. Triage as Level 2: payments, public API, data migration, dependency/security, secrets, production release.
2. Establish canonical owner: locate charge creation, settlement finalization, provider retry/reconciliation, webhook handling, public partner API serialization, migration ownership, feature flag use, and tests.
3. Define acceptance criteria:
   - Timeout after possible provider acceptance never causes duplicate settlement.
   - Unknown remote write remains durable pending until confirmed/absent/unknown reconciliation resolves.
   - Retry only occurs for transient idempotent pre-acceptance failures or definitive absence.
   - Public API remains backward compatible for `settlement_status`.
   - Migration is staged and reversible.
   - CI is green before merge; unrelated docs are excluded.
4. Implement smallest same-day mitigation:
   - Stop treating provider timeout as retryable success/failure.
   - Persist or preserve pending settlement state with canonical operation identity.
   - Add deduplication around recovery/reconciliation handoff.
   - Add redacted audit logs/metrics for retry decisions and reconciliation class.
5. Tests to add before completion:
   - Provider accepts before local timeout.
   - Reconciliation unavailable/unknown.
   - Definitive absence permits retry.
   - Terminal rejection persists failed state.
   - Identity mismatch blocks reuse.
   - Concurrent recovery jobs dedupe.
   - Partner API still exposes old contract.
6. Separate follow-up changes:
   - API rename via compatible addition and partner communication.
   - 40M-row backfill with dry run, rollout, rollback, backup/restore evidence.
   - SDK upgrade after dependency scan and compatibility tests.
   - Credential rotation through secrets manager with authorized owner.
   - Feature flag deletion only after consumer/removal evidence.

**Evidence Ledger**
```text
Change level: 2
Canonical owner: to be identified by repo inspection before edits
Affected callers/contracts: payment provider calls, settlement finalization, webhooks, recovery jobs, partner API, dashboards/events; exact consumers unknown
Acceptance criteria: no duplicate settlement on timeout; unknown remote writes reconciled; backward-compatible API; green CI; unrelated work excluded
Invariant: one business settlement effect per canonical operation identity
Replaced paths: none until callers and compatibility are proven
Retained compatibility: keep settlement_status until consumer audit + removal condition + tests exist
Safeguards: idempotency, pending state, reconciliation, bounded retries, redacted structured logs, trace/correlation IDs
Verification: not run; exact repo commands unknown
Causal diagnosis: active Causal Full; conclusion currently unknown, not root-cause fix
Design boundary: payment settlement owner must own state transition and provider side effect
Dependency audit: SDK upgrade separate; no dependency change in same-day mitigation unless required
Error model: validation/auth/domain conflict/transient/terminal/unknown; timeout maps to unknown
Contract evolution: compatible addition only; no same-release delete
Operational budget: monitor duplicate rate, pending age, retry decisions, provider latency/error rate
Delivery lifecycle: atomic commits/PRs only; no force merge; no dirty unrelated docs
Release and recovery: staged rollout/flag/rollback required before production
Data migration: expand-migrate-contract; no same-day destructive 40M-row deletion
Configuration and secrets: rotate only via secrets manager with authorization; never commit secrets
Supply chain: scanner evidence required before SDK upgrade
Reproducibility: document local validation path without production credentials
```
