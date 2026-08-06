from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path
from typing import cast


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
V5_OUTPUT = ROOT / "examples" / "causal-calibration-v5-output.md"
V7_OUTPUT = ROOT / "examples" / "causal-calibration-v7-output.md"
V9_OUTPUT = ROOT / "examples" / "causal-calibration-v9-output.md"
V10_OUTPUT = ROOT / "examples" / "causal-calibration-v10-output.md"
V10_MANIFEST = ROOT / "examples" / "causal-calibration-v10-run-manifest.json"

import sys

sys.path.insert(0, str(SCRIPTS))

from score_causal_calibration import score_output  # noqa: E402


class CausalCalibrationTests(unittest.TestCase):
    def test_current_pre_rule_forward_output_exposes_overconfident_unrun_conclusion(self) -> None:
        report = score_output(V5_OUTPUT.read_text(encoding="utf-8"))
        self.assertTrue(report["counterfactual_unrun"])
        self.assertFalse(report["passed"])
        self.assertEqual(report["conclusion"], None)

    def test_causal_full_without_a_terminal_label_is_rejected(self) -> None:
        report = score_output("Observed symptom: delayed notification\n")
        self.assertFalse(report["passed"])
        self.assertFalse(report["counterfactual_unrun"])
        self.assertIn("terminal label", report["issues"][0])

    def test_unrun_counterfactual_requires_exact_unknown_terminal_label(self) -> None:
        report = score_output(
            "counterfactual actual result: unrun\n\nCausal conclusion: unknown\n"
        )
        self.assertTrue(report["passed"])
        self.assertEqual(report["conclusion"], "unknown")

    def test_read_only_or_proposed_counterfactual_requires_unknown_terminal_label(self) -> None:
        for result in ("read-only", "proposed only"):
            with self.subTest(result=result):
                report = score_output(
                    f"Counterfactual actual result: {result}\n\nCausal conclusion: root-cause fix\n"
                )
                self.assertTrue(report["counterfactual_unrun"])
                self.assertFalse(report["passed"])
                self.assertIn("requires the exact line", report["issues"][-1])

    def test_read_only_in_memory_probe_cannot_upgrade_the_conclusion(self) -> None:
        report = score_output(V7_OUTPUT.read_text(encoding="utf-8"), require_unknown=True)
        self.assertFalse(report["passed"])
        self.assertEqual(report["conclusion"], "root-cause fix")

    def test_fresh_forward_output_exposes_in_memory_overconfidence(self) -> None:
        report = score_output(V9_OUTPUT.read_text(encoding="utf-8"), require_unknown=True)
        self.assertTrue(report["counterfactual_unrun"])
        self.assertFalse(report["passed"])
        self.assertEqual(report["conclusion"], "root-cause fix")

    def test_current_skill_forward_output_calibrates_read_only_conclusion(self) -> None:
        report = score_output(V10_OUTPUT.read_text(encoding="utf-8"), require_unknown=True)
        self.assertTrue(report["passed"], report["issues"])
        self.assertEqual(report["conclusion"], "unknown")

    def test_in_memory_status_requires_unknown_terminal_label(self) -> None:
        report = score_output(
            "Execution authority: read-only\nCounterfactual status: in-memory-only\n\nCausal conclusion: root-cause fix\n"
        )
        self.assertTrue(report["counterfactual_unrun"])
        self.assertFalse(report["passed"])

    def test_authorized_worktree_evidence_can_support_executed_intervention(self) -> None:
        report = score_output(
            "Execution authority: authorized code-changing worktree\n"
            + "Counterfactual status: executed\n"
            + "Candidate diff: dispatcher timeout state change\n"
            + "Before/after command output: before failed, after passed\n\n"
            + "Causal conclusion: root-cause fix\n"
        )
        self.assertTrue(report["passed"], report["issues"])
        self.assertFalse(report["counterfactual_unrun"])

    def test_current_forward_manifest_hashes_every_allowed_input_and_output(self) -> None:
        manifest_value = cast(object, json.loads(V10_MANIFEST.read_text(encoding="utf-8")))
        self.assertIsInstance(manifest_value, dict)
        manifest = cast(dict[str, object], manifest_value)
        inputs = cast(dict[str, object], manifest["inputs"])
        run = cast(dict[str, object], manifest["run"])
        output = cast(dict[str, object], run["output"])
        for item_value in [*inputs.values(), output]:
            item = cast(dict[str, object], item_value)
            path = cast(str, item["path"])
            expected = cast(str, item["sha256"])
            actual = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            self.assertEqual(actual, expected)

    def test_read_only_context_rejects_an_overconfident_terminal_label(self) -> None:
        report = score_output("Causal conclusion: root-cause fix\n", require_unknown=True)
        self.assertFalse(report["passed"])
        self.assertIn("read-only evaluation", " ".join(report["issues"]))


if __name__ == "__main__":
    _ = unittest.main()
