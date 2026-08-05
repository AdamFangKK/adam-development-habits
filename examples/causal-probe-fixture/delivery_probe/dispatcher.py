from __future__ import annotations

from delivery_probe.model import DeliveryEvent, DispatchRecord, DurableLedger, RecordingQueue
from delivery_probe.provider import EmailProvider, RetryableBeforeAcceptance, TimeoutAfterAcceptance


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

        try:
            record.send_started = True
            record.attempt_count += 1
            delivery = self._provider.send(event, self._attempt_key(event, record))
        except TimeoutAfterAcceptance:
            record.attempt_count += 1
            delivery = self._provider.send(event, self._attempt_key(event, record))
        except RetryableBeforeAcceptance:
            return record

        self._ledger.confirm(record, delivery.delivery_id)
        self._queue.acknowledge(event)
        return record

    @staticmethod
    def _attempt_key(event: DeliveryEvent, record: DispatchRecord) -> str:
        return f"{event.event_id}:{record.attempt_count}"
