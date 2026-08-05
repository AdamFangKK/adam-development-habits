Causal Full record:

- Symptom: after provider timeout, dispatcher could send a second email and acknowledge the queue even though the first provider call may already have accepted.
- Primary hypothesis: `DeliveryDispatcher.dispatch` treated `TimeoutAfterAcceptance` as retryable immediately and generated a new attempt-scoped idempotency key.
- Alternative hypotheses: dashboard over-counting; provider idempotency failure; ledger confirmation on pending records.
- Timeline evidence: `release-timeline.md` says the 2026-07-31 retry refactor changed provider key from full operation identity to `event_id:attempt`; reports followed on 2026-08-02.
- Causal owner: `delivery_probe/dispatcher.py`, specifically the pending timeout decision and provider idempotency key selection.
- Path: provider timeout -> dispatcher timeout branch/new key -> second provider send -> ledger confirm + queue ack -> duplicate delivery / premature completion.
- Counterfactual intervention: keep timeout result pending, use `event.operation_identity` as the provider idempotency key, and reconcile pending started records before retrying. Expected: no second send or ack on first timeout; later retry confirms via reconciliation if provider accepted. Actual: public tests changed from 2 failures to all passing.
- Conclusion: root-cause fix.

Changed behavior:

- Modified only `delivery_probe/dispatcher.py`.
- Timeout after possible acceptance now returns a pending record without acking.
- Redelivery reconciles by canonical operation identity and only acknowledges after confirmed delivery.
- Retryable pre-acceptance failures remain retryable after reconciliation proves absence.

Verification:

- `python3 -m py_compile delivery_probe/dispatcher.py` -> exit 0.
- `python3 -m unittest discover -s tests` -> exact final result:

```text
....
----------------------------------------------------------------------
Ran 4 tests in 0.000s

OK
```

Note: `git diff --check` was unavailable because the fixture is not a Git repository. Debug-leftover scan of `delivery_probe/dispatcher.py` found no matches.
