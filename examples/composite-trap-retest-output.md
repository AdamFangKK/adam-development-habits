Using `$adam-development-habits`, this is a **Level 2 compound change**: money movement, ambiguous remote writes, public API/schema migration, secrets, dependency supply chain, release, CI/Git hygiene, and reproducibility are all triggered. The requested same-day bundle is not safe to implement as one release.

**Observed facts**

- Duplicate settlement effects are observed after provider timeouts.
- The provider may have accepted a charge even when the local caller timed out.
- No trace, reproduction, or confirmed causal path exists yet.
- `settlement_status` has unknown dynamic dashboard, event, and external partner consumers.
- CI, migrations, dashboards, secrets manager, dependency scanner, and feature flags exist, but exact commands/configuration are unknown.
- The worktree contains unrelated documentation from another developer.
- No production credential, deployment permission, or CI exception has been granted.
- A new developer must validate the critical path locally without production credentials.

**Hypotheses**

- Primary: duplicate effects are caused by treating timeout outcomes as retryable failures instead of reconciling unknown remote-write state by canonical operation identity.
- Alternative: duplicate effects are caused by missing/incorrect idempotency keys, recovery job deduplication gaps, webhook replay handling, or mismatched provider confirmation identity.
- Discriminating check: inspect trace/log/payment records for one duplicated settlement and verify whether retries, provider confirmations, webhook acknowledgements, and local finalization used the same canonical identity. Unavailable here because I was instructed not to inspect the repository or runtime evidence.

**Plan**

1. **Mitigate duplicate settlement first; do not retry every timed-out charge.** Treat timed-out provider writes as `unknown`, persist pending state before the provider call, reconcile by canonical identity, and resend only after definitive absence or retryable pre-acceptance rejection. Add structured retry-decision logs with trace/correlation IDs and no payment payload or personal data.

2. **Add regression coverage before behavior changes.** Cover provider acceptance before timeout, unavailable reconciliation, identity mismatch, terminal rejection, retryable pre-acceptance rejection, acknowledgement failure after durable confirmation, and concurrent recovery-job deduplication.

3. **Stage API/schema evolution separately.** Do not rename `settlement_status` to `settlement_state` and delete the old column in the same release. Use expand-migrate-contract: add compatible `settlement_state`, keep `settlement_status`, audit consumers, backfill under measured stop conditions, switch readers/writers after contract tests, and delete only after consumer/removal evidence.

4. **Keep the feature flag.** For a core workflow alteration, use the existing feature flag as rollout and rollback control. Deleting it in the same release removes the recovery mechanism.

5. **Handle credential rotation through the secrets manager only.** Do not put credential values in code, logs, commits, tickets, or evidence. Rotate with owner/access review, expiry/rollback plan, and environment-specific validation. No production rotation without authorization.

6. **Handle the vulnerable transitive SDK as its own supply-chain change unless it is required for the payment mitigation.** Record advisory, dependency path, lockfile impact, compatibility evidence, rollback path, and scanner result.

7. **Reject force-merge and dirty-worktree commit.** Required CI must be green or have an approved scoped exception. Exclude unrelated documentation. Commit only the verified atomic payment mitigation, then separate migration, secret, dependency, and release PRs.

8. **Release safely.** Deploy with the flag disabled, stage exposure, monitor duplicate-settlement rate, provider timeout/reconciliation classes, pending queue age, error rate, and latency. Define stop condition and rollback owner before production.

**Evidence Ledger**

```text
Change level: 2
Canonical owner: Unknown until repository owner/callers are inspected; expected payment settlement/provider-write boundary.
Affected callers/contracts: Public partner API, dashboards, events, migrations, webhook handling, recovery jobs, CI/release workflow; exact consumers unknown.
Acceptance criteria: Timed-out provider writes are preserved as pending/unknown; no duplicate settlement finalization on timeout/retry/recovery; public API remains backward compatible; migration is reversible; CI is green; secrets are redacted; local validation works without production credentials.
Invariant: A settlement side effect is finalized at most once for a canonical operation identity that includes all side-effect-defining dimensions.
Replaced paths: None approved yet. Any unsafe timeout retry path may be replaced only after owner/caller evidence.
Retained compatibility: Keep settlement_status and the existing feature flag until consumer audit, contract tests, rollout metrics, and deletion condition exist.
Safeguards: Ambiguous remote-write reconciliation; idempotency; bounded retry; structured redacted logs; trace/correlation IDs; migration expand-migrate-contract; feature-flag rollback; secret-manager rotation; dependency scan; green CI; atomic Git scope.
Verification: Not run; task constraints allowed only reading the skill and scenario. Project-specific commands are unknown.
Causal diagnosis: Activated, Causal Full required. Current conclusion: unknown. Observations do not prove root cause.
Design boundary: Payment settlement/provider adapter should own remote-write classification and reconciliation; exact owner unknown.
Dependency audit: SDK upgrade staged separately unless proven necessary for mitigation.
Extension decision: No new abstraction proposed without owner/caller evidence.
Data ownership: Settlement store is expected authoritative owner; exact lifecycle/privacy boundary unknown.
Error model: validation/precondition, transient dependency, terminal dependency, and unknown remote-write outcome must be stable typed outcomes.
Contract evolution: Compatible addition first; no same-release public rename/delete.
Operational budget: Monitor duplicate rate, timeout rate, reconciliation unknown rate, pending age, latency, and error rate.
Delivery lifecycle: Separate atomic PRs; no force merge; no unrelated dirty files.
Release and recovery: Feature-flagged rollout with disabled default, monitoring window, stop condition, rollback owner.
Data migration: Expand/backfill/switch/contract with dry-run and backup/restore evidence before destructive deletion.
Configuration and secrets: Rotate only via secrets manager with redacted evidence and rollback.
Supply chain: Scanner/advisory/lockfile/compatibility evidence required before SDK change.
Operational knowledge: ADR/runbook required for reconciliation and incident recovery.
Reproducibility: Local non-secret fixture and documented start/check/test path required.
```
