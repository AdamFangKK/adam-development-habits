#!/usr/bin/env python3
"""Exercise causal diagnosis for duplicate notification delivery.

The scenario models an accepted-but-unobserved provider call, queue redelivery,
duplicate upstream events, process restart, concurrent consumers, acknowledgement
failure, and expiry of provider idempotency-key retention. The intervention uses
a durable operation identity and a three-state reconciliation contract.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
from threading import Lock
from typing import Optional, cast, final
import unittest


class DeliveryTimeout(Exception):
    """The provider accepted the request but the caller cannot observe the result."""


class SimulatedProcessCrash(RuntimeError):
    """The caller terminates after provider acceptance and before local confirmation."""


class QueueAcknowledgementFailure(RuntimeError):
    """The durable state is confirmed but the queue acknowledgement fails."""


class OperationIdentityConflict(RuntimeError):
    """One business event is associated with incompatible side-effect details."""


class ProviderRejected(RuntimeError):
    """The provider rejected the operation before accepting the side effect."""

    def __init__(self, retryable: bool, reason: str) -> None:
        self.retryable: bool = retryable
        self.reason: str = reason
        super().__init__("provider rejected the operation before accepting it")


class FirstSendOutcome(str, Enum):
    SUCCESS = "success"
    TIMEOUT = "timeout"
    CRASH = "crash"
    REJECTED_RETRYABLE = "rejected_retryable"
    REJECTED_TERMINAL = "rejected_terminal"


class ReconciliationStatus(str, Enum):
    FOUND = "found"
    NOT_FOUND = "not_found"
    UNKNOWN = "unknown"
    IDENTITY_CONFLICT = "identity_conflict"


@dataclass(frozen=True)
class NotificationMessage:
    message_id: str
    business_event_id: str
    recipient: str
    template_version: str = "receipt-v1"
    trace_id: str = "trace-notification-42"


@dataclass(frozen=True)
class AcceptedDelivery:
    delivery_id: str
    business_event_id: str
    operation_fingerprint: str
    idempotency_key: str


@dataclass(frozen=True)
class DispatchRecord:
    business_event_id: str
    operation_fingerprint: str
    idempotency_key: str
    state: str
    provider_delivery_id: str | None
    failure_reason: str | None


@dataclass(frozen=True)
class Reconciliation:
    status: ReconciliationStatus
    delivery: AcceptedDelivery | None = None


def operation_fingerprint(message: NotificationMessage) -> str:
    identity = "\x00".join((message.business_event_id, message.recipient, message.template_version))
    return hashlib.sha256(identity.encode()).hexdigest()


@dataclass(frozen=True)
class AuditEvent:
    trace_id: str
    operation_reference: str
    outcome: str


@final
class DispatchAudit:
    """Captures retry decisions using opaque session-local operation references."""

    def __init__(self) -> None:
        self.events: list[AuditEvent] = []
        self._operation_references: dict[str, str] = {}
        self._lock = Lock()

    def record(self, message: NotificationMessage, outcome: str) -> None:
        with self._lock:
            fingerprint = operation_fingerprint(message)
            reference = self._operation_references.setdefault(
                fingerprint,
                f"operation-{len(self._operation_references) + 1}",
            )
            self.events.append(AuditEvent(message.trace_id, reference, outcome))


def record_outcome(audit: DispatchAudit, message: NotificationMessage, outcome: str) -> None:
    audit.record(message, outcome)


@final
class EmailProvider:
    """Provider with expiring key storage and a fallible identity-based lookup."""

    def __init__(self, first_send_outcome: FirstSendOutcome = FirstSendOutcome.TIMEOUT) -> None:
        self._accepted_by_key: dict[str, AcceptedDelivery] = {}
        self._accepted_by_business_event: dict[str, list[AcceptedDelivery]] = {}
        self._first_send_outcome = first_send_outcome
        self._first_attempted_events: set[str] = set()
        self._next_delivery_number = 1
        self._reconciliation_available = True
        self._lock = Lock()

    def send(self, message: NotificationMessage, idempotency_key: str) -> AcceptedDelivery:
        with self._lock:
            first_attempt = message.business_event_id not in self._first_attempted_events
            if first_attempt:
                self._first_attempted_events.add(message.business_event_id)
                if self._first_send_outcome in {
                    FirstSendOutcome.REJECTED_RETRYABLE,
                    FirstSendOutcome.REJECTED_TERMINAL,
                }:
                    if self._first_send_outcome is FirstSendOutcome.REJECTED_RETRYABLE:
                        raise ProviderRejected(True, "transient_provider_rejection")
                    raise ProviderRejected(False, "invalid_recipient")

            delivery = self._accepted_by_key.get(idempotency_key)
            if delivery is None:
                delivery = AcceptedDelivery(
                    delivery_id=f"provider-{self._next_delivery_number}",
                    business_event_id=message.business_event_id,
                    operation_fingerprint=operation_fingerprint(message),
                    idempotency_key=idempotency_key,
                )
                self._next_delivery_number += 1
                self._accepted_by_key[idempotency_key] = delivery
                self._accepted_by_business_event.setdefault(message.business_event_id, []).append(delivery)

            if first_attempt:
                if self._first_send_outcome is FirstSendOutcome.TIMEOUT:
                    raise DeliveryTimeout("provider accepted the delivery before the network timeout")
                if self._first_send_outcome is FirstSendOutcome.CRASH:
                    raise SimulatedProcessCrash("process terminated after provider acceptance")
            return delivery

    def reconcile(self, message: NotificationMessage) -> Reconciliation:
        """Return found, absent, unknown, or an identity conflict without resending."""
        with self._lock:
            if not self._reconciliation_available:
                return Reconciliation(ReconciliationStatus.UNKNOWN)

            deliveries = self._accepted_by_business_event.get(message.business_event_id, [])
            if not deliveries:
                return Reconciliation(ReconciliationStatus.NOT_FOUND)

            matching = [delivery for delivery in deliveries if delivery.operation_fingerprint == operation_fingerprint(message)]
            if len(deliveries) == 1 and len(matching) == 1:
                return Reconciliation(ReconciliationStatus.FOUND, matching[0])
            return Reconciliation(ReconciliationStatus.IDENTITY_CONFLICT)

    def set_reconciliation_available(self, available: bool) -> None:
        with self._lock:
            self._reconciliation_available = available

    def expire_idempotency_keys(self) -> None:
        """Model provider key expiry while retained delivery history remains queryable."""
        with self._lock:
            self._accepted_by_key.clear()

    def accepted_count_for(self, business_event_id: str) -> int:
        with self._lock:
            return len(self._accepted_by_business_event.get(business_event_id, []))


@final
class DurableDispatchLedger:
    """Persist one operation identity, key, and confirmed delivery per business event."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        with self._connect() as connection:
            _ = connection.execute(
                """
                CREATE TABLE IF NOT EXISTS dispatch_ledger (
                    business_event_id TEXT PRIMARY KEY,
                    operation_fingerprint TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    state TEXT NOT NULL CHECK (state IN ('pending', 'confirmed', 'failed')),
                    provider_delivery_id TEXT UNIQUE,
                    failure_reason TEXT
                )
                """
            )
            _ = connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reconciliation_recovery (
                    business_event_id TEXT PRIMARY KEY,
                    operation_fingerprint TEXT NOT NULL
                )
                """
            )

    def start(self, message: NotificationMessage) -> DispatchRecord:
        fingerprint = operation_fingerprint(message)
        idempotency_key = "notification:" + fingerprint
        with self._connect() as connection:
            _ = connection.execute(
                """
                INSERT OR IGNORE INTO dispatch_ledger
                    (business_event_id, operation_fingerprint, idempotency_key, state, provider_delivery_id, failure_reason)
                VALUES (?, ?, ?, 'pending', NULL, NULL)
                """,
                (message.business_event_id, fingerprint, idempotency_key),
            )
        record = self.record_for(message.business_event_id)
        assert record is not None
        if record.operation_fingerprint != fingerprint:
            raise OperationIdentityConflict("the same business event cannot change recipient or template version")
        return record

    def mark_confirmed(self, message: NotificationMessage, provider_delivery_id: str) -> DispatchRecord:
        with self._connect() as connection:
            _ = connection.execute("BEGIN IMMEDIATE")
            record = self._record_for(connection, message.business_event_id)
            if record is None:
                raise AssertionError("a provider delivery cannot precede its durable business event")
            if record.operation_fingerprint != operation_fingerprint(message):
                raise OperationIdentityConflict("provider confirmation does not match the durable operation identity")
            if record.state == "failed":
                raise AssertionError("a terminally failed operation cannot become confirmed")
            if record.provider_delivery_id not in {None, provider_delivery_id}:
                raise AssertionError("one business event cannot confirm different provider deliveries")
            _ = connection.execute(
                """
                UPDATE dispatch_ledger
                SET state = 'confirmed', provider_delivery_id = ?, failure_reason = NULL
                WHERE business_event_id = ?
                """,
                (provider_delivery_id, message.business_event_id),
            )
        confirmed = self.record_for(message.business_event_id)
        assert confirmed is not None
        return confirmed

    def mark_failed(self, message: NotificationMessage, failure_reason: str) -> DispatchRecord:
        with self._connect() as connection:
            _ = connection.execute("BEGIN IMMEDIATE")
            record = self._record_for(connection, message.business_event_id)
            if record is None:
                raise AssertionError("a terminal failure cannot precede its durable business event")
            if record.operation_fingerprint != operation_fingerprint(message):
                raise OperationIdentityConflict("terminal failure does not match the durable operation identity")
            if record.state == "confirmed":
                raise AssertionError("a confirmed operation cannot become terminally failed")
            if record.state == "failed":
                if record.failure_reason != failure_reason:
                    raise AssertionError("a terminal failure reason cannot change")
                return record
            _ = connection.execute(
                "UPDATE dispatch_ledger SET state = 'failed', failure_reason = ? WHERE business_event_id = ?",
                (failure_reason, message.business_event_id),
            )
        failed = self.record_for(message.business_event_id)
        assert failed is not None
        return failed

    def schedule_reconciliation_recovery(self, message: NotificationMessage) -> None:
        with self._connect() as connection:
            _ = connection.execute("BEGIN IMMEDIATE")
            record = self._record_for(connection, message.business_event_id)
            if record is None or record.state != "pending":
                raise AssertionError("reconciliation recovery requires a durable pending operation")
            fingerprint = operation_fingerprint(message)
            if record.operation_fingerprint != fingerprint:
                raise OperationIdentityConflict("recovery job does not match the durable operation identity")
            _ = connection.execute(
                """
                INSERT OR IGNORE INTO reconciliation_recovery (business_event_id, operation_fingerprint)
                VALUES (?, ?)
                """,
                (message.business_event_id, fingerprint),
            )

    def recovery_job_count_for(self, business_event_id: str) -> int:
        with self._connect() as connection:
            row = cast(
                Optional[tuple[int]],
                connection.execute(
                    "SELECT COUNT(*) FROM reconciliation_recovery WHERE business_event_id = ?",
                    (business_event_id,),
                ).fetchone(),
            )
        assert row is not None
        return int(row[0])

    def recovery_job_fingerprint_for(self, business_event_id: str) -> str | None:
        with self._connect() as connection:
            row = cast(
                Optional[tuple[str]],
                connection.execute(
                    "SELECT operation_fingerprint FROM reconciliation_recovery WHERE business_event_id = ?",
                    (business_event_id,),
                ).fetchone(),
            )
        return row[0] if row is not None else None

    def record_for(self, business_event_id: str) -> DispatchRecord | None:
        with self._connect() as connection:
            return self._record_for(connection, business_event_id)

    def record_count_for(self, business_event_id: str) -> int:
        with self._connect() as connection:
            row = cast(
                Optional[tuple[int]],
                connection.execute(
                    "SELECT COUNT(*) FROM dispatch_ledger WHERE business_event_id = ?",
                    (business_event_id,),
                ).fetchone(),
            )
        assert row is not None
        return int(row[0])

    @staticmethod
    def _record_for(connection: sqlite3.Connection, business_event_id: str) -> DispatchRecord | None:
        row = cast(
            Optional[tuple[str, str, str, str, Optional[str], Optional[str]]],
            connection.execute(
                """
                SELECT business_event_id, operation_fingerprint, idempotency_key, state, provider_delivery_id, failure_reason
                FROM dispatch_ledger WHERE business_event_id = ?
                """,
                (business_event_id,),
            ).fetchone(),
        )
        return DispatchRecord(*row) if row is not None else None

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._database_path, timeout=5.0)


@final
class RecordingQueue:
    """Acknowledgement boundary that can fail after durable confirmation."""

    def __init__(self, fail_next_acknowledgement: bool = False) -> None:
        self.acknowledged_message_ids: list[str] = []
        self._fail_next_acknowledgement = fail_next_acknowledgement
        self._lock = Lock()

    def acknowledge(self, message: NotificationMessage, ledger: DurableDispatchLedger) -> None:
        record = ledger.record_for(message.business_event_id)
        if record is None or record.operation_fingerprint != operation_fingerprint(message):
            raise OperationIdentityConflict("acknowledgement does not match the durable operation identity")
        if record.state != "confirmed" or record.provider_delivery_id is None:
            raise AssertionError("queue messages must not be acknowledged before durable confirmation")
        with self._lock:
            if self._fail_next_acknowledgement:
                self._fail_next_acknowledgement = False
                raise QueueAcknowledgementFailure("queue acknowledgement failed after durable confirmation")
            self.acknowledged_message_ids.append(message.message_id)

    def acknowledge_recovery_handoff(
        self,
        message: NotificationMessage,
        ledger: DurableDispatchLedger,
        audit: DispatchAudit,
    ) -> None:
        record = ledger.record_for(message.business_event_id)
        fingerprint = operation_fingerprint(message)
        if record is None or record.operation_fingerprint != fingerprint:
            record_outcome(audit, message, "identity_conflict")
            raise OperationIdentityConflict("recovery handoff does not match the durable operation identity")
        if ledger.recovery_job_fingerprint_for(message.business_event_id) != fingerprint:
            record_outcome(audit, message, "identity_conflict")
            raise OperationIdentityConflict("recovery job does not match the durable operation identity")
        if record.state != "pending" or ledger.recovery_job_count_for(message.business_event_id) != 1:
            raise AssertionError("recovery handoff requires a durable pending operation and recovery job")
        with self._lock:
            self.acknowledged_message_ids.append(message.message_id)
        record_outcome(audit, message, "recovery_handoff_acknowledged")

    def acknowledge_terminal_failure(
        self,
        message: NotificationMessage,
        ledger: DurableDispatchLedger,
        audit: DispatchAudit,
    ) -> None:
        record = ledger.record_for(message.business_event_id)
        if record is None or record.operation_fingerprint != operation_fingerprint(message):
            record_outcome(audit, message, "identity_conflict")
            raise OperationIdentityConflict("terminal acknowledgement does not match the durable operation identity")
        if record.state != "failed" or record.failure_reason is None:
            raise AssertionError("terminal acknowledgement requires a durable failure reason")
        with self._lock:
            self.acknowledged_message_ids.append(message.message_id)
        record_outcome(audit, message, "terminal_failure_acknowledged")


def acknowledge_and_record(
    queue: RecordingQueue,
    ledger: DurableDispatchLedger,
    message: NotificationMessage,
    audit: DispatchAudit,
    outcome: str,
) -> str:
    try:
        queue.acknowledge(message, ledger)
    except QueueAcknowledgementFailure:
        record_outcome(audit, message, "acknowledgement_failed")
        raise
    record_outcome(audit, message, outcome)
    return outcome


def dispatch_with_transport_key(provider: EmailProvider, message: NotificationMessage, attempt: int) -> str:
    """Legacy behavior: every queue delivery and retry gets a new provider key."""
    key = f"transport:{message.message_id}:attempt:{attempt}"
    try:
        _ = provider.send(message, key)
    except DeliveryTimeout:
        return "ambiguous"
    return "sent"


def dispatch_with_business_key(
    provider: EmailProvider,
    ledger: DurableDispatchLedger,
    queue: RecordingQueue,
    message: NotificationMessage,
    audit: DispatchAudit,
) -> str:
    """Reconcile safely, send only after absence, and acknowledge after confirmation."""
    try:
        record = ledger.start(message)
    except OperationIdentityConflict:
        record_outcome(audit, message, "identity_conflict")
        raise
    if record.state == "confirmed":
        return acknowledge_and_record(queue, ledger, message, audit, "already_confirmed")
    if record.state == "failed":
        record_outcome(audit, message, "terminal_failure")
        return "terminal_failure"

    reconciliation = provider.reconcile(message)
    if reconciliation.status is ReconciliationStatus.FOUND:
        assert reconciliation.delivery is not None
        _ = ledger.mark_confirmed(message, reconciliation.delivery.delivery_id)
        return acknowledge_and_record(queue, ledger, message, audit, "reconciled")
    if reconciliation.status is ReconciliationStatus.UNKNOWN:
        record_outcome(audit, message, "reconciliation_unknown")
        return "reconciliation_unknown"
    if reconciliation.status is ReconciliationStatus.IDENTITY_CONFLICT:
        record_outcome(audit, message, "identity_conflict")
        raise OperationIdentityConflict("provider history conflicts with the requested operation identity")

    assert reconciliation.status is ReconciliationStatus.NOT_FOUND
    try:
        delivery = provider.send(message, record.idempotency_key)
    except DeliveryTimeout:
        record_outcome(audit, message, "ambiguous")
        return "ambiguous"
    except ProviderRejected as error:
        if error.retryable:
            record_outcome(audit, message, "definitive_failure_retryable")
            return "definitive_failure_retryable"
        _ = ledger.mark_failed(message, error.reason)
        record_outcome(audit, message, "terminal_failure")
        return "terminal_failure"
    except SimulatedProcessCrash:
        record_outcome(audit, message, "process_crash")
        raise

    _ = ledger.mark_confirmed(message, delivery.delivery_id)
    return acknowledge_and_record(queue, ledger, message, audit, "sent")


@final
class CausalNotificationExperiment(unittest.TestCase):
    primary: NotificationMessage = NotificationMessage("", "", "")
    duplicate: NotificationMessage = NotificationMessage("", "", "")
    audit: DispatchAudit = DispatchAudit()

    def setUp(self) -> None:  # pyright: ignore[reportImplicitOverride]
        self.primary = NotificationMessage("queue-100", "invoice-42:receipt", "customer@example.invalid")
        self.duplicate = NotificationMessage("queue-101", "invoice-42:receipt", "customer@example.invalid")
        self.audit = DispatchAudit()

    def test_transport_attempt_keys_reproduce_three_external_deliveries(self) -> None:
        provider = EmailProvider()

        self.assertEqual(dispatch_with_transport_key(provider, self.primary, attempt=1), "ambiguous")
        self.assertEqual(dispatch_with_transport_key(provider, self.primary, attempt=2), "sent")
        self.assertEqual(dispatch_with_transport_key(provider, self.duplicate, attempt=1), "sent")

        self.assertEqual(provider.accepted_count_for(self.primary.business_event_id), 3)

    def test_ambiguous_timeout_is_not_acknowledged_before_durable_confirmation(self) -> None:
        provider = EmailProvider()
        queue = RecordingQueue()
        with tempfile.TemporaryDirectory() as directory:
            ledger = DurableDispatchLedger(Path(directory) / "dispatch-ledger.sqlite")

            self.assertEqual(dispatch_with_business_key(provider, ledger, queue, self.primary, self.audit), "ambiguous")

            self.assertEqual(queue.acknowledged_message_ids, [])
            record = ledger.record_for(self.primary.business_event_id)
            self.assertIsNotNone(record)
            assert record is not None
            self.assertEqual(record.state, "pending")
            self.assertIsNone(record.provider_delivery_id)
            self.assertEqual(ledger.record_count_for(self.primary.business_event_id), 1)
            self.assertEqual([event.outcome for event in self.audit.events], ["ambiguous"])

    def test_durable_identity_survives_timeout_restart_and_concurrent_duplicate_delivery(self) -> None:
        for round_number in range(10):
            with self.subTest(round_number=round_number):
                provider = EmailProvider()
                queue = RecordingQueue()
                audit = DispatchAudit()
                with tempfile.TemporaryDirectory() as directory:
                    database_path = Path(directory) / "dispatch-ledger.sqlite"
                    first_process_ledger = DurableDispatchLedger(database_path)

                    self.assertEqual(
                        dispatch_with_business_key(provider, first_process_ledger, queue, self.primary, audit),
                        "ambiguous",
                    )
                    self.assertEqual(queue.acknowledged_message_ids, [])

                    left_process_ledger = DurableDispatchLedger(database_path)
                    right_process_ledger = DurableDispatchLedger(database_path)

                    def reconcile_duplicate(
                        ledger: DurableDispatchLedger,
                        message: NotificationMessage,
                    ) -> str:
                        return dispatch_with_business_key(provider, ledger, queue, message, audit)

                    with ThreadPoolExecutor(max_workers=2) as executor:
                        outcomes = list(
                            executor.map(
                                reconcile_duplicate,
                                (left_process_ledger, right_process_ledger),
                                (self.primary, self.duplicate),
                            )
                        )

                    self.assertIn("reconciled", outcomes)
                    self.assertTrue(
                        all(outcome in {"reconciled", "already_confirmed"} for outcome in outcomes),
                        outcomes,
                    )
                    self.assertEqual(provider.accepted_count_for(self.primary.business_event_id), 1)
                    self.assertEqual(left_process_ledger.record_count_for(self.primary.business_event_id), 1)
                    record = right_process_ledger.record_for(self.primary.business_event_id)
                    self.assertIsNotNone(record)
                    assert record is not None
                    self.assertEqual(record.state, "confirmed")
                    self.assertIsNotNone(record.provider_delivery_id)
                    self.assertCountEqual(queue.acknowledged_message_ids, ["queue-100", "queue-101"])
                    self.assertEqual(audit.events[0].outcome, "ambiguous")
                    self.assertEqual(len(audit.events), 3)
                    self.assertTrue(
                        all(event.outcome in {"reconciled", "already_confirmed"} for event in audit.events[1:])
                    )

    def test_expired_provider_key_requires_reconciliation_before_late_retry(self) -> None:
        provider = EmailProvider()
        queue = RecordingQueue()
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "dispatch-ledger.sqlite"
            first_process_ledger = DurableDispatchLedger(database_path)

            self.assertEqual(
                dispatch_with_business_key(provider, first_process_ledger, queue, self.primary, self.audit),
                "ambiguous",
            )
            provider.expire_idempotency_keys()

            restarted_process_ledger = DurableDispatchLedger(database_path)
            self.assertEqual(
                dispatch_with_business_key(provider, restarted_process_ledger, queue, self.duplicate, self.audit),
                "reconciled",
            )
            self.assertEqual(provider.accepted_count_for(self.primary.business_event_id), 1)
            self.assertEqual(
                dispatch_with_business_key(provider, restarted_process_ledger, queue, self.primary, self.audit),
                "already_confirmed",
            )
            self.assertEqual(provider.accepted_count_for(self.primary.business_event_id), 1)
            self.assertEqual(restarted_process_ledger.record_count_for(self.primary.business_event_id), 1)
            self.assertCountEqual(queue.acknowledged_message_ids, ["queue-101", "queue-100"])
            self.assertEqual(
                [event.outcome for event in self.audit.events],
                ["ambiguous", "reconciled", "already_confirmed"],
            )

    def test_expired_provider_key_without_reconciliation_can_duplicate_a_delivery(self) -> None:
        provider = EmailProvider()
        key = "notification:" + operation_fingerprint(self.primary)

        with self.assertRaises(DeliveryTimeout):
            _ = provider.send(self.primary, key)
        provider.expire_idempotency_keys()
        _ = provider.send(self.primary, key)

        self.assertEqual(provider.accepted_count_for(self.primary.business_event_id), 2)

    def test_unknown_reconciliation_does_not_resend_or_acknowledge(self) -> None:
        provider = EmailProvider()
        queue = RecordingQueue()
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "dispatch-ledger.sqlite"
            first_process_ledger = DurableDispatchLedger(database_path)
            self.assertEqual(
                dispatch_with_business_key(provider, first_process_ledger, queue, self.primary, self.audit),
                "ambiguous",
            )
            provider.set_reconciliation_available(False)

            restarted_process_ledger = DurableDispatchLedger(database_path)
            self.assertEqual(
                dispatch_with_business_key(provider, restarted_process_ledger, queue, self.duplicate, self.audit),
                "reconciliation_unknown",
            )
            self.assertEqual(provider.accepted_count_for(self.primary.business_event_id), 1)
            self.assertEqual(queue.acknowledged_message_ids, [])
            record = restarted_process_ledger.record_for(self.primary.business_event_id)
            self.assertIsNotNone(record)
            assert record is not None
            self.assertEqual(record.state, "pending")
            self.assertEqual([event.outcome for event in self.audit.events], ["ambiguous", "reconciliation_unknown"])

            provider.set_reconciliation_available(True)
            self.assertEqual(
                dispatch_with_business_key(provider, restarted_process_ledger, queue, self.duplicate, self.audit),
                "reconciled",
            )
            self.assertEqual(provider.accepted_count_for(self.primary.business_event_id), 1)
            self.assertEqual(queue.acknowledged_message_ids, ["queue-101"])
            self.assertEqual(
                [event.outcome for event in self.audit.events],
                ["ambiguous", "reconciliation_unknown", "reconciled"],
            )

    def test_unknown_reconciliation_can_ack_after_durable_recovery_handoff(self) -> None:
        provider = EmailProvider()
        queue = RecordingQueue()
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "dispatch-ledger.sqlite"
            first_process_ledger = DurableDispatchLedger(database_path)
            self.assertEqual(
                dispatch_with_business_key(provider, first_process_ledger, queue, self.primary, self.audit),
                "ambiguous",
            )
            provider.set_reconciliation_available(False)

            restarted_process_ledger = DurableDispatchLedger(database_path)
            self.assertEqual(
                dispatch_with_business_key(provider, restarted_process_ledger, queue, self.duplicate, self.audit),
                "reconciliation_unknown",
            )
            left_process_ledger = DurableDispatchLedger(database_path)
            right_process_ledger = DurableDispatchLedger(database_path)

            def schedule_recovery(ledger: DurableDispatchLedger) -> None:
                ledger.schedule_reconciliation_recovery(self.duplicate)

            with ThreadPoolExecutor(max_workers=2) as executor:
                _ = list(
                    executor.map(
                        schedule_recovery,
                        (left_process_ledger, right_process_ledger),
                    )
                )
            queue.acknowledge_recovery_handoff(self.duplicate, restarted_process_ledger, self.audit)

            self.assertEqual(provider.accepted_count_for(self.primary.business_event_id), 1)
            self.assertEqual(restarted_process_ledger.recovery_job_count_for(self.primary.business_event_id), 1)
            self.assertEqual(queue.acknowledged_message_ids, ["queue-101"])
            self.assertEqual(
                [event.outcome for event in self.audit.events],
                ["ambiguous", "reconciliation_unknown", "recovery_handoff_acknowledged"],
            )

    def test_identity_conflict_blocks_reuse_of_a_business_event(self) -> None:
        provider = EmailProvider()
        queue = RecordingQueue()
        conflicting_message = NotificationMessage(
            "queue-102",
            self.primary.business_event_id,
            "other-customer@example.invalid",
        )
        with tempfile.TemporaryDirectory() as directory:
            ledger = DurableDispatchLedger(Path(directory) / "dispatch-ledger.sqlite")
            self.assertEqual(dispatch_with_business_key(provider, ledger, queue, self.primary, self.audit), "ambiguous")

            with self.assertRaises(OperationIdentityConflict):
                _ = dispatch_with_business_key(provider, ledger, queue, conflicting_message, self.audit)

            ledger.schedule_reconciliation_recovery(self.primary)
            with self.assertRaises(OperationIdentityConflict):
                queue.acknowledge_recovery_handoff(conflicting_message, ledger, self.audit)

            self.assertEqual(provider.accepted_count_for(self.primary.business_event_id), 1)
            self.assertEqual(queue.acknowledged_message_ids, [])
            self.assertEqual(ledger.record_count_for(self.primary.business_event_id), 1)
            self.assertEqual(
                [event.outcome for event in self.audit.events],
                ["ambiguous", "identity_conflict", "identity_conflict"],
            )

    def test_crash_after_provider_acceptance_recovers_without_a_second_delivery(self) -> None:
        provider = EmailProvider(FirstSendOutcome.CRASH)
        queue = RecordingQueue()
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "dispatch-ledger.sqlite"
            first_process_ledger = DurableDispatchLedger(database_path)

            with self.assertRaises(SimulatedProcessCrash):
                _ = dispatch_with_business_key(provider, first_process_ledger, queue, self.primary, self.audit)

            self.assertEqual(provider.accepted_count_for(self.primary.business_event_id), 1)
            self.assertEqual(queue.acknowledged_message_ids, [])
            restarted_process_ledger = DurableDispatchLedger(database_path)
            self.assertEqual(
                dispatch_with_business_key(provider, restarted_process_ledger, queue, self.duplicate, self.audit),
                "reconciled",
            )
            self.assertEqual(provider.accepted_count_for(self.primary.business_event_id), 1)
            self.assertEqual(queue.acknowledged_message_ids, ["queue-101"])
            self.assertEqual([event.outcome for event in self.audit.events], ["process_crash", "reconciled"])

    def test_acknowledgement_failure_retries_without_a_second_delivery(self) -> None:
        provider = EmailProvider(FirstSendOutcome.SUCCESS)
        queue = RecordingQueue(fail_next_acknowledgement=True)
        with tempfile.TemporaryDirectory() as directory:
            ledger = DurableDispatchLedger(Path(directory) / "dispatch-ledger.sqlite")

            with self.assertRaises(QueueAcknowledgementFailure):
                _ = dispatch_with_business_key(provider, ledger, queue, self.primary, self.audit)

            record = ledger.record_for(self.primary.business_event_id)
            self.assertIsNotNone(record)
            assert record is not None
            self.assertEqual(record.state, "confirmed")
            self.assertEqual(provider.accepted_count_for(self.primary.business_event_id), 1)
            self.assertEqual(queue.acknowledged_message_ids, [])
            self.assertEqual(
                dispatch_with_business_key(provider, ledger, queue, self.duplicate, self.audit),
                "already_confirmed",
            )
            self.assertEqual(provider.accepted_count_for(self.primary.business_event_id), 1)
            self.assertEqual(queue.acknowledged_message_ids, ["queue-101"])
            self.assertEqual([event.outcome for event in self.audit.events], ["acknowledgement_failed", "already_confirmed"])

    def test_acknowledgement_rejects_a_mismatched_operation_identity(self) -> None:
        queue = RecordingQueue()
        conflicting_message = NotificationMessage(
            "queue-102",
            self.primary.business_event_id,
            "other-customer@example.invalid",
        )
        with tempfile.TemporaryDirectory() as directory:
            ledger = DurableDispatchLedger(Path(directory) / "dispatch-ledger.sqlite")
            _ = ledger.start(self.primary)
            _ = ledger.mark_confirmed(self.primary, "provider-1")

            with self.assertRaises(OperationIdentityConflict):
                queue.acknowledge(conflicting_message, ledger)

            self.assertEqual(queue.acknowledged_message_ids, [])
            queue.acknowledge(self.primary, ledger)
            self.assertEqual(queue.acknowledged_message_ids, ["queue-100"])

    def test_retryable_rejection_can_retry_with_auditable_operation_identity(self) -> None:
        provider = EmailProvider(FirstSendOutcome.REJECTED_RETRYABLE)
        queue = RecordingQueue()
        with tempfile.TemporaryDirectory() as directory:
            ledger = DurableDispatchLedger(Path(directory) / "dispatch-ledger.sqlite")

            self.assertEqual(
                dispatch_with_business_key(provider, ledger, queue, self.primary, self.audit),
                "definitive_failure_retryable",
            )
            self.assertEqual(provider.accepted_count_for(self.primary.business_event_id), 0)
            self.assertEqual(queue.acknowledged_message_ids, [])
            self.assertEqual([event.outcome for event in self.audit.events], ["definitive_failure_retryable"])
            self.assertEqual(self.audit.events[0].trace_id, self.primary.trace_id)
            self.assertEqual(self.audit.events[0].operation_reference, "operation-1")

            self.assertEqual(dispatch_with_business_key(provider, ledger, queue, self.primary, self.audit), "sent")
            self.assertEqual(provider.accepted_count_for(self.primary.business_event_id), 1)
            self.assertEqual(queue.acknowledged_message_ids, ["queue-100"])
            self.assertEqual([event.outcome for event in self.audit.events], ["definitive_failure_retryable", "sent"])

    def test_terminal_rejection_stays_failed_on_redelivery(self) -> None:
        provider = EmailProvider(FirstSendOutcome.REJECTED_TERMINAL)
        queue = RecordingQueue()
        conflicting_message = NotificationMessage(
            "queue-102",
            self.primary.business_event_id,
            "other-customer@example.invalid",
        )
        with tempfile.TemporaryDirectory() as directory:
            ledger = DurableDispatchLedger(Path(directory) / "dispatch-ledger.sqlite")

            self.assertEqual(
                dispatch_with_business_key(provider, ledger, queue, self.primary, self.audit),
                "terminal_failure",
            )
            record = ledger.record_for(self.primary.business_event_id)
            self.assertIsNotNone(record)
            assert record is not None
            self.assertEqual(record.state, "failed")
            self.assertEqual(record.failure_reason, "invalid_recipient")
            self.assertEqual(provider.accepted_count_for(self.primary.business_event_id), 0)
            self.assertEqual(queue.acknowledged_message_ids, [])

            with self.assertRaises(AssertionError):
                _ = ledger.mark_confirmed(self.primary, "provider-forbidden")
            with self.assertRaises(AssertionError):
                _ = ledger.mark_failed(self.primary, "replacement-reason")
            with self.assertRaises(OperationIdentityConflict):
                queue.acknowledge_terminal_failure(conflicting_message, ledger, self.audit)
            self.assertEqual(queue.acknowledged_message_ids, [])
            queue.acknowledge_terminal_failure(self.primary, ledger, self.audit)
            self.assertEqual(queue.acknowledged_message_ids, ["queue-100"])

            self.assertEqual(
                dispatch_with_business_key(provider, ledger, queue, self.duplicate, self.audit),
                "terminal_failure",
            )
            self.assertEqual(provider.accepted_count_for(self.primary.business_event_id), 0)
            self.assertEqual(queue.acknowledged_message_ids, ["queue-100"])
            self.assertEqual(
                [event.outcome for event in self.audit.events],
                ["terminal_failure", "identity_conflict", "terminal_failure_acknowledged", "terminal_failure"],
            )


def experiment_report() -> dict[str, int | str]:
    return {
        "ack_failure_recovery_delivery_count": 1,
        "ambiguous_timeout_ack_count": 0,
        "conclusion": "root_cause_fix",
        "crash_recovery_delivery_count": 1,
        "durable_operation_identity_delivery_count": 1,
        "durable_ledger_record_count": 1,
        "retryable_rejection_delivery_count": 1,
        "recovery_handoff_ack_count": 1,
        "recovery_handoff_delivery_count": 1,
        "terminal_rejection_delivery_count": 0,
        "terminal_rejection_ack_count": 1,
        "terminal_identity_conflict_ack_count": 0,
        "identity_conflict_delivery_count": 1,
        "late_retry_after_provider_key_expiry_delivery_count": 1,
        "legacy_transport_key_delivery_count": 3,
        "scenario": "notification_timeout_ack_reconciliation_identity_expiry_concurrency",
        "unknown_reconciliation_ack_count": 0,
        "unknown_reconciliation_delivery_count": 1,
        "unreconciled_expired_provider_key_delivery_count": 2,
    }


if __name__ == "__main__":
    report_mode = "--report" in sys.argv
    program = unittest.main(argv=[sys.argv[0]], exit=False)
    if program.result.wasSuccessful():
        if report_mode:
            print(json.dumps(experiment_report(), sort_keys=True))
        else:
            print("Causal conclusion: root-cause fix")
            print("Rejected alternative: an unavailable provider lookup is proof that a prior operation is absent")
            print("Supported hypothesis: transport-derived keys and unsafe retry after expired provider retention split one business event")
            print("Intervention: durable operation identity, three-state reconciliation, and confirmation-gated acknowledgement")
    else:
        raise SystemExit(1)
