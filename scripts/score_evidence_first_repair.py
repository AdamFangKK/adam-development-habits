#!/usr/bin/env python3
"""Score a repair response against the evidence-first repair gate."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TypedDict


@dataclass(frozen=True)
class Gate:
    identifier: str
    description: str
    matches: Callable[[str], bool]


class GateResult(TypedDict):
    id: str
    passed: bool
    description: str


class ScoreReport(TypedDict):
    score: int
    maximum_score: int
    passed: bool
    critical_misses: list[str]
    results: list[GateResult]


def has_all(text: str, *terms: str) -> bool:
    return all(term in text for term in terms)


def has_complete_failed_attempt_ledger(text: str) -> bool:
    """Check ledger fields together instead of borrowing keywords from unrelated prose."""
    marker = "failed-attempt ledger"
    start = text.find(marker)
    if start < 0:
        return False

    # Keep the check format-agnostic while binding evidence to the ledger entry.
    # A ledger may be prose or a table row, but its required fields must be in
    # the same record rather than borrowed from a later verification section.
    ledger = text[start:].splitlines()[0]
    has_result = any(term in ledger for term in ("actual result", "result:", "result was"))
    has_category = any(
        term in ledger
        for term in ("failure category", "wrong-owner", "observability-gap", "test-gap")
    )
    has_next_constraint = any(
        term in ledger
        for term in (
            "new evidence",
            "evidence required",
            "next constraint",
            "next probe",
            "next check",
            "required before repeating",
            "unavailable",
        )
    )
    return has_result and has_category and has_next_constraint


def has_counterfactual_calibration(text: str) -> bool:
    """Bind counterfactual status to its record and require calibrated unknowns."""
    marker = "counterfactual status"
    record = next((line for line in text.splitlines() if marker in line), "")
    if not record:
        return False
    if not has_all(record, "execution authority", "counterfactual status"):
        return False
    if "counterfactual status: executed" in record:
        return "before/after" in record
    if "counterfactual status: unrun" in record:
        return "causal conclusion: unknown" in text and "before/after" not in record
    return False


def has_deployment_runtime_verification(text: str) -> bool:
    """Require deployment and runtime evidence to occur in the same record."""
    return any(
        re.search(r"deployment[^.\n;]{0,40}runtime[^.\n;]{0,40}(verification|verify)", line) is not None
        for line in text.splitlines()
    )


def has_explicit_production_authority_stop(text: str) -> bool:
    """Require an explicit prohibition or authorization boundary for production actions."""
    return any(
        phrase in text
        for phrase in (
            "no production action without authorization",
            "no production action is authorized",
            "production action is not authorized",
            "production action requires authorization",
        )
    )


GATES = (
    Gate(
        "symptom-invariant",
        "Separates the observed symptom from the violated invariant.",
        lambda text: has_all(text, "symptom", "invariant"),
    ),
    Gate(
        "full-path",
        "Maps the complete request/state path and side effect to the symptom.",
        lambda text: (
            ("request/state path" in text or "request/state" in text or "causal path" in text or "path:" in text)
            and "->" in text
            and "symptom" in text
        ),
    ),
    Gate(
        "observability-gap",
        "Names observable nodes and blind spots and instruments or preserves unknowns.",
        lambda text: (
            ("observable" in text or "observability" in text)
            and has_all(text, "blind", "instrument", "unknown")
        ),
    ),
    Gate(
        "hypothesis-alternative",
        "States a primary hypothesis and a plausible alternative.",
        lambda text: (
            ("primary hypothesis" in text or ("h1" in text and "primary" in text))
            and ("alternative hypothesis" in text or ("h2" in text and "alternative" in text))
        ),
    ),
    Gate(
        "discriminating-probe",
        "Runs a falsifiable discriminating probe.",
        lambda text: has_all(text, "discriminating probe", "reject"),
    ),
    Gate(
        "earliest-owner",
        "Changes the earliest responsible owner rather than the visible symptom.",
        lambda text: has_all(text, "earliest responsible owner", "owner"),
    ),
    Gate(
        "failed-attempt-ledger",
        "Records prior attempts and prevents repeating a failure category without evidence.",
        has_complete_failed_attempt_ledger,
    ),
    Gate(
        "counterfactual-calibration",
        "Records authority, counterfactual status, and before/after evidence.",
        has_counterfactual_calibration,
    ),
    Gate(
        "verification-and-risk",
        "Runs regression and deployment/runtime verification and records residual risk.",
        lambda text: (
            "regression" in text
            and has_deployment_runtime_verification(text)
            and ("residual risk" in text or "remaining risk" in text or "remaining risks" in text)
        ),
    ),
    Gate(
        "stop-conditions",
        "Stops unsupported completion claims when evidence is missing or ownership is unresolved.",
        lambda text: (
            "stop" in text
            and (
                "do not claim completion" in text
                or "before calling a code change complete" in text
                or ("root-cause claim" in text and "possible" in text)
                or ("counterfactual status: unrun" in text and "causal conclusion: unknown" in text)
            )
            and has_explicit_production_authority_stop(text)
        ),
    ),
)


def score_response(response: str) -> ScoreReport:
    normalized = response.casefold()
    results: list[GateResult] = []
    for gate in GATES:
        passed = gate.matches(normalized)
        results.append({"id": gate.identifier, "passed": passed, "description": gate.description})
    misses = [result["id"] for result in results if not result["passed"]]
    return {
        "score": len(GATES) - len(misses),
        "maximum_score": len(GATES),
        "passed": not misses,
        "critical_misses": misses,
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Score an evidence-first repair response.")
    parser.add_argument("response", type=Path, help="Plain-text response to score")
    arguments = parser.parse_args()
    report = score_response(arguments.response.read_text(encoding="utf-8"))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
