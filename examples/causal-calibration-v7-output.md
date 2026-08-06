Likely causal owner: `DeliveryDispatcher.dispatch`, specifically the `except TimeoutAfterAcceptance` branch plus `_attempt_key`.

Causal path: provider timeout after possible acceptance -> dispatcher treats unknown remote-write outcome as retryable -> increments attempt count -> sends again with a new idempotency key (`event_id:attempt`) -> confirms the second delivery -> acknowledges the queue event. That violates the safe remote-write contract: unknown provider outcome must remain pending until reconciliation proves `FOUND` or `ABSENT`.

Minimal safe intervention:

- Use the canonical `event.operation_identity` as the provider idempotency key, not `event_id:attempt`.
- On `TimeoutAfterAcceptance`, return the durable pending record with no ack and no second send.
- On redelivery of a pending record with `send_started=True`, call `provider.reconcile(event.operation_identity)`.
- If reconciliation is `FOUND` and identity matches, confirm and ack.
- If `ABSENT`, issue a new idempotent send.
- If `UNKNOWN`, preserve pending with no send and no ack.

Evidence:

- `dispatcher.py`: timeout handler immediately calls `provider.send(...)` again after incrementing `attempt_count`.
- `dispatcher.py`: `_attempt_key()` changes the provider key per attempt, defeating provider idempotency.
- `provider.py`: provider idempotency is keyed only by caller-supplied key; `reconcile(operation_identity)` is the intended timeout recovery path.
- `dashboard.py`: dashboard only reads `provider.delivery_count`; it cannot cause sends or acknowledgements.
- `release-timeline.md`: duplicate alerts began after the retry refactor changed keys from full operation identity to `event_id:attempt`.
- Fresh fixture test run: `python3 -m unittest discover ...` ran 4 tests, 2 failed. Failures showed current behavior returns `confirmed` instead of `pending`, and produces `provider.delivery_count == 2` instead of `1`.
- In-memory counterfactual changing only dispatcher behavior produced: `timeout_first pending 1 []`, `timeout_redelivery confirmed confirmed 1 [...]`, and `pre_acceptance pending confirmed 1 [...]`.

Causal conclusion: root-cause fix
