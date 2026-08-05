from __future__ import annotations

from delivery_probe.model import DeliveryEvent, DispatchRecord, DurableLedger, RecordingQueue
from delivery_probe.provider import EmailProvider, ReconciliationState, RetryableBeforeAcceptance, TimeoutAfterAcceptance


class DeliveryDispatcher:
    def __init__(self, ledger: DurableLedger, provider: EmailProvider, queue: RecordingQueue) -> None:
        self._ledger = ledger
        self._provider = provider
        self._queue = queue

    def dispatch(self, event: DeliveryEvent) -> DispatchRecord:
        record = self._ledger.start(event)
        if record.state == "confirmed":
            self._queue.acknowledge(event)
            return record
        if record.send_started:
            reconciliation = self._provider.reconcile(event.operation_identity)
            if reconciliation.state is ReconciliationState.FOUND and reconciliation.delivery is not None:
                self._ledger.confirm(record, reconciliation.delivery.delivery_id)
                self._queue.acknowledge(event)
                return record
            if reconciliation.state is ReconciliationState.UNKNOWN:
                return record

        try:
            record.send_started = True
            record.attempt_count += 1
            delivery = self._provider.send(event, self._attempt_key(event, record))
        except TimeoutAfterAcceptance:
            return record
        except RetryableBeforeAcceptance:
            return record

        self._ledger.confirm(record, delivery.delivery_id)
        self._queue.acknowledge(event)
        return record

    @staticmethod
    def _attempt_key(event: DeliveryEvent, record: DispatchRecord) -> str:
        return event.operation_identity
