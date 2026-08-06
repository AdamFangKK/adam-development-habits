Calibrated conclusion label: **root-cause owner identified, high confidence; no fix applied because this was read-only.**

The causal owner is `DeliveryDispatcher.dispatch`, specifically the timeout handling and idempotency-key decision. On `TimeoutAfterAcceptance`, it immediately performs a second provider `send` (`dispatcher.py:23-25`) after incrementing `attempt_count`; `_attempt_key` uses `event_id:attempt_count` (`dispatcher.py:34-35`), so the retry uses a new provider key. The provider is explicitly idempotent only by caller-supplied key (`provider.py:37-38`, `provider.py:54-57`), and `timeout_after_acceptance` accepts the delivery before raising (`provider.py:65-67`). That makes the second send a distinct accepted delivery, after which the dispatcher confirms and acknowledges the queue event (`dispatcher.py:29-30`).

Minimal safe intervention: treat provider timeout after a possible remote write as **UNKNOWN**, not retryable success/failure. Keep the ledger record pending, do not acknowledge the queue event, and do not immediately resend. On redelivery or recovery, call `provider.reconcile(event.operation_identity)`: `FOUND` with matching canonical identity may confirm and ack; `ABSENT` may issue a new idempotent send using the stable canonical `event.operation_identity`; `UNKNOWN` remains pending or is handed to a deduplicated recovery path without ack.

Evidence:

- Release timeline says the retry refactor changed the provider key from full operation identity to `event_id:attempt`, and duplicate alerts appeared after provider timeouts.
- `dashboard.py` only reads `provider.delivery_count`, so it is a symptom surface, not the sender.
- Public tests reproduce the failure: expected pending/no ack after timeout, actual `confirmed`; expected one provider delivery after retry, actual `2`.
- Manual probe showed `record_state=confirmed`, `attempt_count=2`, `provider_delivery_count=2`, acknowledged queue identity present, and provider keys `event-17:1` plus `event-17:2`.

Counterfactual actual result: unrun.
