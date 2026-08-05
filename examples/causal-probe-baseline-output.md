Changed only `delivery_probe/dispatcher.py`.

Diagnosis: after `TimeoutAfterAcceptance`, the dispatcher immediately retried with a new `event_id:attempt` provider key, so an accepted-but-timed-out send could be delivered twice and then acknowledged as complete.

Changed behavior: pending records now reconcile by `operation_identity` before any retry. Timeouts remain pending without a second send or queue ack; confirmed reconciliation records are acknowledged; retries use the stable operation identity as the provider idempotency key.

Verification:
`python3 -m unittest discover -s tests -v`

Result:
`Ran 4 tests in 0.000s`
`OK`

Syntax check:
`python3 -m py_compile delivery_probe/dispatcher.py` passed.
