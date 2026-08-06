Calibrated conclusion label: **unknown**.

Execution authority: read-only
Counterfactual status: in-memory-only
Diff/before-after output gate: absent

Observed symptom: provider timeouts can be followed by duplicate email deliveries, and the queue event is acknowledged even though the provider may already have accepted the original send.

Candidate owner: `DeliveryDispatcher.dispatch`, specifically the timeout branch plus `_attempt_key`.
Path: `timeout_after_acceptance` -> dispatcher treats the ambiguous result as retryable -> increments attempt count and resends with a new key -> confirms and acknowledges -> duplicate delivery alert.

Minimal safe intervention, if authorized later:
- Treat `TimeoutAfterAcceptance` as `UNKNOWN`.
- Keep the durable record pending.
- Do not acknowledge the queue event.
- Do not resend immediately.
- On redelivery, call `provider.reconcile(event.operation_identity)`.
- Confirm and ack only when reconciliation returns `FOUND` for the same canonical identity.

Evidence:
- `dispatcher.py` currently resends inside the timeout handler and uses an attempt-scoped send key.
- `provider.py` says idempotency is keyed by the caller-supplied key and exposes `reconcile(operation_identity)`.
- `release-timeline.md` ties the regression to the retry refactor that switched from full operation identity to `event_id:attempt`.
- `dashboard.py` only reads `provider.delivery_count`; it is a symptom surface, not the sender.
- The public fixture test run failed on the current code: timeout-after-acceptance returned `confirmed` instead of `pending`, and provider delivery count was `2` instead of `1`.

Residual uncertainty:
- No authorized code-changing worktree diff was produced.
- The in-memory probe is consistent with the candidate owner, but under the current gate it does not upgrade the conclusion.

Causal conclusion: unknown
