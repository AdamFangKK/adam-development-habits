Calibrated conclusion label: **root-cause fix**.

The causal owner is `DeliveryDispatcher.dispatch`, specifically the `TimeoutAfterAcceptance` branch plus `_attempt_key`.
On timeout after a possible acceptance, it immediately performs a second provider send with a new attempt-scoped key, then confirms and acknowledges the queue event. That turns an ambiguous remote-write result into a duplicate delivery plus a success ack.

Minimal safe intervention:
- Treat `TimeoutAfterAcceptance` as `UNKNOWN`, not success and not retryable proof.
- Keep the ledger record pending.
- Do not acknowledge the queue event.
- Do not resend immediately.
- On redelivery, call `provider.reconcile(event.operation_identity)`.
- If reconciliation is `FOUND` with the same canonical identity, confirm and ack.
- If `ABSENT`, issue a new idempotent send with the canonical operation identity.
- If `UNKNOWN`, preserve pending and hand off to recovery.

Evidence:
- `dispatcher.py` shows the timeout branch resends immediately and `_attempt_key` changes the provider key per attempt.
- `provider.py` says idempotency is keyed by caller-supplied key and exposes `reconcile(operation_identity)` for timeout recovery.
- `release-timeline.md` ties the duplicate-alert regression to the retry refactor that changed the provider key to `event_id:attempt`.
- `dashboard.py` only reads `provider.delivery_count`; it cannot originate sends or acknowledgements.
- The fixture test run failed on the current code: timeout-after-acceptance returned `confirmed` instead of `pending`, and provider delivery count was `2` instead of `1`.
- The in-memory counterfactual that changed only dispatcher behavior produced `timeout_first pending 1 []`, `timeout_redelivery confirmed confirmed 1 [...]`, and `pre_acceptance pending confirmed 1 [...]`.

Causal conclusion: root-cause fix
