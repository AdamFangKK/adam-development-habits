from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

from delivery_probe.model import DeliveryEvent


class TimeoutAfterAcceptance(Exception):
    pass


class RetryableBeforeAcceptance(Exception):
    pass


class ReconciliationState(str, Enum):
    FOUND = "found"
    ABSENT = "absent"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ProviderDelivery:
    delivery_id: str
    operation_identity: str
    idempotency_key: str


@dataclass(frozen=True)
class Reconciliation:
    state: ReconciliationState
    delivery: ProviderDelivery | None = None


class EmailProvider:
    """Provider idempotency is intentionally keyed by the caller-supplied key."""

    def __init__(
        self,
        outcomes: Iterable[str] = (),
        reconciliation_states: Iterable[ReconciliationState] = (),
    ) -> None:
        self._outcomes = list(outcomes)
        self._reconciliation_states = list(reconciliation_states)
        self._deliveries_by_key: dict[str, ProviderDelivery] = {}
        self._delivery_sequence = 0

    @property
    def delivery_count(self) -> int:
        return len(self._deliveries_by_key)

    def send(self, event: DeliveryEvent, idempotency_key: str) -> ProviderDelivery:
        existing = self._deliveries_by_key.get(idempotency_key)
        if existing is not None:
            return existing

        outcome = self._outcomes.pop(0) if self._outcomes else "accept"
        if outcome == "retryable_before_acceptance":
            raise RetryableBeforeAcceptance()
        if outcome == "timeout_without_acceptance":
            raise TimeoutAfterAcceptance()

        delivery = self._accept(event, idempotency_key)
        if outcome == "timeout_after_acceptance":
            raise TimeoutAfterAcceptance()
        if outcome != "accept":
            raise ValueError(f"unknown provider outcome: {outcome}")
        return delivery

    def reconcile(self, operation_identity: str) -> Reconciliation:
        if self._reconciliation_states:
            state = self._reconciliation_states.pop(0)
            if state is ReconciliationState.UNKNOWN:
                return Reconciliation(state)
            if state is ReconciliationState.ABSENT:
                return Reconciliation(state)

        matches = [delivery for delivery in self._deliveries_by_key.values() if delivery.operation_identity == operation_identity]
        if len(matches) == 1:
            return Reconciliation(ReconciliationState.FOUND, matches[0])
        if not matches:
            return Reconciliation(ReconciliationState.ABSENT)
        return Reconciliation(ReconciliationState.UNKNOWN)

    def _accept(self, event: DeliveryEvent, idempotency_key: str) -> ProviderDelivery:
        self._delivery_sequence += 1
        delivery = ProviderDelivery(
            delivery_id=f"delivery-{self._delivery_sequence}",
            operation_identity=event.operation_identity,
            idempotency_key=idempotency_key,
        )
        self._deliveries_by_key[idempotency_key] = delivery
        return delivery
