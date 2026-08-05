from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FIXTURE = ROOT / "examples" / "causal-probe-fixture"
REFERENCE = ROOT / "examples" / "causal-probe-reference-dispatcher.py"

import sys

sys.path.insert(0, str(SCRIPTS))

from score_causal_probe import ALLOWED_CHANGE, HIDDEN_TEST, score_candidate  # noqa: E402


class CausalProbeScoreTests(unittest.TestCase):
    def create_candidate(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary_directory = tempfile.TemporaryDirectory(prefix="adam-causal-probe-test-")
        candidate = Path(temporary_directory.name) / "candidate"
        _ = shutil.copytree(FIXTURE, candidate)
        return temporary_directory, candidate

    def test_buggy_fixture_fails_the_public_contract(self) -> None:
        temporary_directory, candidate = self.create_candidate()
        with temporary_directory:
            report = score_candidate(candidate)
        self.assertFalse(report["public"]["passed"])
        self.assertFalse(report["passed"])

    def test_reference_repair_passes_public_and_hidden_contracts(self) -> None:
        temporary_directory, candidate = self.create_candidate()
        with temporary_directory:
            _ = shutil.copyfile(REFERENCE, candidate / ALLOWED_CHANGE)
            report = score_candidate(candidate)
        self.assertEqual(report["changed_paths"], [str(ALLOWED_CHANGE)])
        self.assertTrue(report["public"]["passed"], report["public"]["stderr"])
        self.assertTrue(report["hidden"]["passed"], report["hidden"]["stderr"])
        self.assertTrue(report["passed"])

    def test_event_id_only_mitigation_passes_public_but_fails_hidden_identity_contract(self) -> None:
        temporary_directory, candidate = self.create_candidate()
        with temporary_directory:
            reference = REFERENCE.read_text(encoding="utf-8")
            candidate_dispatcher = candidate / ALLOWED_CHANGE
            _ = candidate_dispatcher.write_text(
                reference.replace("event.operation_identity", "event.event_id"),
                encoding="utf-8",
            )
            report = score_candidate(candidate)
        self.assertTrue(report["public"]["passed"], report["public"]["stderr"])
        self.assertFalse(report["hidden"]["passed"])
        self.assertFalse(report["passed"])

    def test_test_tampering_is_rejected_even_when_behavior_is_correct(self) -> None:
        temporary_directory, candidate = self.create_candidate()
        with temporary_directory:
            _ = shutil.copyfile(REFERENCE, candidate / ALLOWED_CHANGE)
            test_file = candidate / "tests" / "test_dispatcher.py"
            _ = test_file.write_text(test_file.read_text(encoding="utf-8") + "\n# unauthorized mutation\n", encoding="utf-8")
            report = score_candidate(candidate)
        self.assertIn("tests/test_dispatcher.py", report["changed_paths"])
        self.assertFalse(report["only_canonical_owner_changed"])
        self.assertFalse(report["passed"])

    def test_hidden_contract_covers_unknown_reconciliation_and_full_identity(self) -> None:
        self.assertIn("UNKNOWN", HIDDEN_TEST)
        self.assertIn("tenant-b", HIDDEN_TEST)
        self.assertIn("timeout_without_acceptance", HIDDEN_TEST)


if __name__ == "__main__":
    _ = unittest.main()
