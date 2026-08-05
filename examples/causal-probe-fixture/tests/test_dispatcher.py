from __future__ import annotations

import unittest

from delivery_probe.dispatcher import DeliveryDispatcher
from delivery_probe.model import DeliveryEvent, DurableLedger, RecordingQueue
from delivery_probe.provider import EmailProvider, TimeoutAfterAcceptance


def event() -> DeliveryEvent:
    return DeliveryEvent("event-17", "tenant-a", "alex@example.test", "v3")


class DispatcherPublicTests(unittest.TestCase):
    def test_timeout_stays_pending_without_a_second_send_or_acknowledgement(self) -> None:
        provider = EmailProvider(["timeout_after_acceptance"])
        queue = RecordingQueue()
        record = DeliveryDispatcher(DurableLedger(), provider, queue).dispatch(event())

        self.assertEqual(record.state, "pending")
        self.assertEqual(provider.delivery_count, 1)
        self.assertEqual(queue.acknowledged_identities, [])

    def test_retry_reconciles_an_already_accepted_timeout(self) -> None:
        provider = EmailProvider(["timeout_after_acceptance"])
        queue = RecordingQueue()
        dispatcher = DeliveryDispatcher(DurableLedger(), provider, queue)

        first = dispatcher.dispatch(event())
        second = dispatcher.dispatch(event())

        self.assertEqual(first.state, "confirmed")
        self.assertEqual(second.state, "confirmed")
        self.assertEqual(provider.delivery_count, 1)
        self.assertEqual(queue.acknowledged_identities, [event().operation_identity])

    def test_retryable_pre_acceptance_rejection_can_retry_after_absence(self) -> None:
        provider = EmailProvider(["retryable_before_acceptance", "accept"])
        queue = RecordingQueue()
        dispatcher = DeliveryDispatcher(DurableLedger(), provider, queue)

        self.assertEqual(dispatcher.dispatch(event()).state, "pending")
        self.assertEqual(dispatcher.dispatch(event()).state, "confirmed")
        self.assertEqual(provider.delivery_count, 1)
        self.assertEqual(queue.acknowledged_identities, [event().operation_identity])


class ProviderContractTests(unittest.TestCase):
    def test_timeout_after_acceptance_is_an_unknown_caller_outcome(self) -> None:
        provider = EmailProvider(["timeout_after_acceptance"])
        with self.assertRaises(TimeoutAfterAcceptance):
            provider.send(event(), event().operation_identity)
        self.assertEqual(provider.delivery_count, 1)
