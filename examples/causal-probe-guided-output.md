**symptom**

After a provider timeout that may have occurred after acceptance, the dispatcher sends again with a new idempotency key, creating duplicate provider deliveries and then acknowledging the queue event as confirmed.

**alternative hypotheses**

1. Dashboard false positive: rejected. `dashboard.py` only reads `provider.delivery_count > 1`; it cannot send or acknowledge.
2. Queue acknowledgement bug: rejected as primary. `RecordingQueue.acknowledge` only records an identity passed by dispatcher; it does not decide confirmation.
3. Provider idempotency failure: rejected as primary. Provider idempotency is explicitly caller-keyed; dispatcher supplies changing keys.
4. Dispatcher retry/key policy regression: supported. `TimeoutAfterAcceptance` path retries immediately with `event_id:attempt`.

**timeline**

2026-07-31: retry refactor changed provider key from full operation identity to `event_id:attempt`; provider supports idempotency only per caller key and exposes `reconcile(operation_identity)`.

2026-08-02: duplicate delivery alerts appeared after provider timeouts.

2026-08-04: acknowledgements were observed after a second send attempt, while first-call acceptance was unproven.

**causal owner**

`trigger -> decision/state owner -> side effect -> symptom`:

`TimeoutAfterAcceptance from EmailProvider.send -> DeliveryDispatcher.dispatch retry/ack decision plus _attempt_key identity choice -> second provider send under a different idempotency key and later queue ack -> duplicate email / unsafe acknowledgement`.

First divergent decision: `DeliveryDispatcher.dispatch` treats an ambiguous accepted-timeout as retryable immediately instead of pending reconciliation.

**counterfactual intervention**

Minimal intervention: on `TimeoutAfterAcceptance`, keep the durable record pending and do not ack; on later dispatch, reconcile by `event.operation_identity` before any resend; use `event.operation_identity` as the provider idempotency key.

Expected result: timeout leaves one provider delivery, pending state, no ack; redelivery reconciles the accepted send and acks once; pre-acceptance retry can still send later.

Actual current reproduction run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests/test_dispatcher.py` failed 2/4 tests. Failures showed `record.state` was `confirmed` instead of `pending`, and `provider.delivery_count` was `2` instead of `1`.

Counterfactual actual result: unrun, because I was instructed not to edit files.

**conclusion classification**

Unknown until the counterfactual diff is applied and verified. The proposed change targets the named causal owner; if the listed verification passes after applying it, classification becomes root-cause fix.

**exact behavioral changes**

- Preserve pending state on ambiguous provider timeout.
- Do not acknowledge the queue after an ambiguous timeout.
- Reconcile a previously started pending send by canonical operation identity before retrying.
- Confirm and acknowledge only after reconciliation finds a matching delivery or a fresh send returns accepted.
- Retry after explicit pre-acceptance rejection without treating it as an ambiguous accepted send.
- Use the full operation identity as the provider idempotency key, not `event_id:attempt`.

**unified diff for dispatcher.py only**

```diff
--- a/delivery_probe/dispatcher.py
+++ b/delivery_probe/dispatcher.py
@@ -2,7 +2,7 @@

 from delivery_probe.model import DeliveryEvent, DispatchRecord, DurableLedger, RecordingQueue
-from delivery_probe.provider import EmailProvider, RetryableBeforeAcceptance, TimeoutAfterAcceptance
+from delivery_probe.provider import EmailProvider, ReconciliationState, RetryableBeforeAcceptance, TimeoutAfterAcceptance


 class DeliveryDispatcher:
@@ -16,19 +16,31 @@
             self._queue.acknowledge(event)
             return record

+        if record.send_started:
+            reconciliation = self._provider.reconcile(event.operation_identity)
+            if reconciliation.state is ReconciliationState.FOUND:
+                delivery = reconciliation.delivery
+                if delivery is None or delivery.operation_identity != event.operation_identity:
+                    return record
+                self._ledger.confirm(record, delivery.delivery_id)
+                self._queue.acknowledge(event)
+                return record
+            if reconciliation.state is ReconciliationState.UNKNOWN:
+                return record
+
         try:
             record.send_started = True
             record.attempt_count += 1
-            delivery = self._provider.send(event, self._attempt_key(event, record))
-        except TimeoutAfterAcceptance:
-            record.attempt_count += 1
-            delivery = self._provider.send(event, self._attempt_key(event, record))
+            delivery = self._provider.send(event, self._attempt_key(event))
         except RetryableBeforeAcceptance:
+            record.send_started = False
+            return record
+        except TimeoutAfterAcceptance:
             return record

        self._ledger.confirm(record, delivery.delivery_id)
         self._queue.acknowledge(event)
         return record

     @staticmethod
-    def _attempt_key(event: DeliveryEvent, record: DispatchRecord) -> str:
-        return f"{event.event_id}:{record.attempt_count}"
+    def _attempt_key(event: DeliveryEvent) -> str:
+        return event.operation_identity
```

**exact verification result you would run**

Unrun after conceptual patch:

`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests/test_dispatcher.py`

Required expected result after applying the diff: all 4 tests pass.
