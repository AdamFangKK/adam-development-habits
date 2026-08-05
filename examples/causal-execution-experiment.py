#!/usr/bin/env python3
"""Demonstrate causal diagnosis before fixing a duplicate-charge symptom.

The experiment rejects a presentation-layer explanation by inspecting the
payment gateway's source-of-truth records. It then changes one variable - the
idempotency key supplied to the gateway - and verifies that retries no longer
create additional charges.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import sys
import unittest


@dataclass(frozen=True)
class Charge:
    order_id: str
    idempotency_key: str


class PaymentGateway:
    def __init__(self) -> None:
        self._charges: dict[str, Charge] = {}

    def charge(self, order_id: str, idempotency_key: str) -> Charge:
        return self._charges.setdefault(idempotency_key, Charge(order_id, idempotency_key))

    def charge_count_for(self, order_id: str) -> int:
        return sum(charge.order_id == order_id for charge in self._charges.values())


def submit_checkout_with_bug(gateway: PaymentGateway, order_id: str, request_id: str, attempt: int) -> Charge:
    """A retry incorrectly creates a new idempotency key for each attempt."""
    return gateway.charge(order_id, f"checkout:{request_id}:attempt:{attempt}")


def submit_checkout_fixed(gateway: PaymentGateway, order_id: str, request_id: str, attempt: int) -> Charge:
    """The attempt is intentionally ignored; one request maps to one charge."""
    del attempt
    return gateway.charge(order_id, f"checkout:{request_id}")


class CausalExecutionExperiment(unittest.TestCase):
    def test_gateway_records_disprove_a_presentation_only_explanation(self) -> None:
        gateway = PaymentGateway()
        submit_checkout_with_bug(gateway, "order-42", "request-7", attempt=1)
        submit_checkout_with_bug(gateway, "order-42", "request-7", attempt=2)

        self.assertEqual(gateway.charge_count_for("order-42"), 2)

    def test_stable_key_intervention_prevents_duplicate_charge(self) -> None:
        gateway = PaymentGateway()
        submit_checkout_fixed(gateway, "order-42", "request-7", attempt=1)
        submit_checkout_fixed(gateway, "order-42", "request-7", attempt=2)

        self.assertEqual(gateway.charge_count_for("order-42"), 1)


def experiment_report() -> dict[str, int | str]:
    return {
        "conclusion": "root_cause_fix",
        "legacy_gateway_charge_count": 2,
        "scenario": "checkout_retry_idempotency",
        "stable_key_gateway_charge_count": 1,
    }


if __name__ == "__main__":
    report_mode = "--report" in sys.argv
    program = unittest.main(argv=[sys.argv[0]], exit=False)
    if program.result.wasSuccessful():
        if report_mode:
            print(json.dumps(experiment_report(), sort_keys=True))
        else:
            print("Causal conclusion: root-cause fix")
            print("Rejected alternative: the UI merely displayed one charge twice")
            print("Supported hypothesis: retries changed the payment idempotency key")
            print("Intervention: derive one stable key from the request ID")
    else:
        raise SystemExit(1)
