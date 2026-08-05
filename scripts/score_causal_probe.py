#!/usr/bin/env python3
"""Score a causal-repair candidate against public and withheld delivery contracts."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TypedDict


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "causal-probe-fixture"
ALLOWED_CHANGE = Path("delivery_probe/dispatcher.py")


HIDDEN_TEST = r'''
from __future__ import annotations

import unittest

from delivery_probe.dispatcher import DeliveryDispatcher
from delivery_probe.model import DeliveryEvent, DurableLedger, RecordingQueue
from delivery_probe.provider import EmailProvider, ReconciliationState


def event(event_id: str = "event-17", tenant_id: str = "tenant-a") -> DeliveryEvent:
    return DeliveryEvent(event_id, tenant_id, "alex@example.test", "v3")


class DispatcherHiddenTests(unittest.TestCase):
    def test_unknown_reconciliation_does_not_resend_or_acknowledge(self) -> None:
        provider = EmailProvider(["timeout_after_acceptance"], [ReconciliationState.UNKNOWN])
        queue = RecordingQueue()
        dispatcher = DeliveryDispatcher(DurableLedger(), provider, queue)

        self.assertEqual(dispatcher.dispatch(event()).state, "pending")
        self.assertEqual(dispatcher.dispatch(event()).state, "pending")
        self.assertEqual(provider.delivery_count, 1)
        self.assertEqual(queue.acknowledged_identities, [])

    def test_identity_includes_tenant_not_only_business_event_id(self) -> None:
        provider = EmailProvider(["accept", "accept"])
        queue = RecordingQueue()
        dispatcher = DeliveryDispatcher(DurableLedger(), provider, queue)

        self.assertEqual(dispatcher.dispatch(event(tenant_id="tenant-a")).state, "confirmed")
        self.assertEqual(dispatcher.dispatch(event(tenant_id="tenant-b")).state, "confirmed")
        self.assertEqual(provider.delivery_count, 2)
        self.assertEqual(len(queue.acknowledged_identities), 2)

    def test_definitive_absence_allows_one_safe_resend(self) -> None:
        provider = EmailProvider(["timeout_without_acceptance", "accept"])
        queue = RecordingQueue()
        dispatcher = DeliveryDispatcher(DurableLedger(), provider, queue)

        self.assertEqual(dispatcher.dispatch(event()).state, "pending")
        self.assertEqual(dispatcher.dispatch(event()).state, "confirmed")
        self.assertEqual(provider.delivery_count, 1)
        self.assertEqual(queue.acknowledged_identities, [event().operation_identity])
'''


class SuiteReport(TypedDict):
    exit_code: int
    stdout: str
    stderr: str
    passed: bool


class CandidateReport(TypedDict):
    allowed_change: str
    changed_paths: list[str]
    only_canonical_owner_changed: bool
    public: SuiteReport
    hidden: SuiteReport
    passed: bool


class Arguments(argparse.Namespace):
    candidate_root: Path = Path()


def source_paths(root: Path) -> set[Path]:
    return {
        path.relative_to(root)
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }


def changed_paths(candidate_root: Path) -> list[str]:
    paths = source_paths(FIXTURE) | source_paths(candidate_root)
    changes: list[str] = []
    for relative_path in paths:
        fixture_path = FIXTURE / relative_path
        candidate_path = candidate_root / relative_path
        if not fixture_path.is_file() or not candidate_path.is_file() or fixture_path.read_bytes() != candidate_path.read_bytes():
            changes.append(str(relative_path))
    return sorted(changes)


def run_suite(candidate_root: Path, test_directory: Path, pattern: str) -> SuiteReport:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", str(test_directory), "-p", pattern, "-v"],
        cwd=candidate_root,
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )
    return {
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "passed": result.returncode == 0,
    }


def score_candidate(candidate_root: Path) -> CandidateReport:
    if not candidate_root.is_dir():
        raise ValueError(f"candidate root does not exist: {candidate_root}")

    changes = changed_paths(candidate_root)
    allowed_changes = changes == [str(ALLOWED_CHANGE)]
    public = run_suite(candidate_root, candidate_root / "tests", "test_*.py")

    with tempfile.TemporaryDirectory(prefix="adam-causal-probe-") as temporary_directory:
        runner_root = Path(temporary_directory) / "candidate"
        _ = shutil.copytree(candidate_root, runner_root, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        hidden_path = runner_root / "tests" / "test_hidden_contract.py"
        _ = hidden_path.write_text(HIDDEN_TEST, encoding="utf-8")
        hidden = run_suite(runner_root, runner_root / "tests", "test_hidden_contract.py")

    return {
        "allowed_change": str(ALLOWED_CHANGE),
        "changed_paths": changes,
        "only_canonical_owner_changed": allowed_changes,
        "public": public,
        "hidden": hidden,
        "passed": allowed_changes and public["passed"] and hidden["passed"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Score a causal-probe repair candidate.")
    _ = parser.add_argument("candidate_root", type=Path, help="Directory copied from the causal probe fixture")
    arguments = parser.parse_args(namespace=Arguments())
    candidate_argument = arguments.candidate_root
    report = score_candidate(candidate_argument.resolve())
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
