from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeliveryEvent:
    event_id: str
    tenant_id: str
    recipient: str
    payload_version: str

    @property
    def operation_identity(self) -> str:
        return "|".join((self.tenant_id, self.event_id, self.recipient, self.payload_version))


@dataclass
class DispatchRecord:
    event: DeliveryEvent
    state: str = "pending"
    send_started: bool = False
    attempt_count: int = 0
    provider_delivery_id: str | None = None


class DurableLedger:
    def __init__(self) -> None:
        self._records: dict[str, DispatchRecord] = {}

    def start(self, event: DeliveryEvent) -> DispatchRecord:
        return self._records.setdefault(event.operation_identity, DispatchRecord(event))

    def confirm(self, record: DispatchRecord, provider_delivery_id: str) -> DispatchRecord:
        record.state = "confirmed"
        record.provider_delivery_id = provider_delivery_id
        return record


class RecordingQueue:
    def __init__(self) -> None:
        self.acknowledged_identities: list[str] = []

    def acknowledge(self, event: DeliveryEvent) -> None:
        if event.operation_identity not in self.acknowledged_identities:
            self.acknowledged_identities.append(event.operation_identity)
