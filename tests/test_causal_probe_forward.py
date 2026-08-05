from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import cast


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FIXTURE = ROOT / "examples" / "causal-probe-fixture"
MANIFEST = ROOT / "examples" / "causal-probe-run-manifest.json"
EVALUATION = ROOT / "examples" / "causal-probe-evaluation.json"
VERIFIER = ROOT / "examples" / "causal-probe-verifier-report.json"

import sys

sys.path.insert(0, str(SCRIPTS))

from score_causal_probe import ALLOWED_CHANGE, run_suite, score_candidate  # noqa: E402


def load_object(path: Path) -> dict[str, object]:
    value = cast(object, json.loads(path.read_text(encoding="utf-8")))
    if not isinstance(value, dict):
        raise AssertionError(f"{path} must contain an object")
    return cast(dict[str, object], value)


def require_object(value: object, name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise AssertionError(f"{name} must be an object")
    return cast(dict[str, object], value)


def require_list(value: object, name: str) -> list[object]:
    if not isinstance(value, list):
        raise AssertionError(f"{name} must be a list")
    return cast(list[object], value)


class CausalProbeForwardTests(unittest.TestCase):
    def test_pristine_fixture_reproduces_the_timeout_failure(self) -> None:
        report = run_suite(FIXTURE, FIXTURE / "tests", "test_*.py")
        self.assertFalse(report["passed"])
        self.assertIn("FAILED (failures=2)", report["stderr"])

    def test_saved_candidates_pass_public_hidden_and_scope_contracts(self) -> None:
        for label in ("baseline", "guided"):
            with self.subTest(candidate=label), tempfile.TemporaryDirectory(prefix="adam-causal-probe-replay-") as temporary_directory:
                candidate_root = Path(temporary_directory) / "candidate"
                _ = shutil.copytree(FIXTURE, candidate_root)
                source = ROOT / "examples" / f"causal-probe-{label}-dispatcher.py"
                _ = shutil.copyfile(source, candidate_root / ALLOWED_CHANGE)
                report = score_candidate(candidate_root)
                self.assertTrue(report["passed"], report["public"]["stderr"] + report["hidden"]["stderr"])
                self.assertEqual(report["changed_paths"], [str(ALLOWED_CHANGE)])

    def test_manifest_and_verifier_hashes_are_current(self) -> None:
        manifest = load_object(MANIFEST)
        inputs = require_object(manifest["inputs"], "inputs")
        runs = require_list(manifest["runs"], "runs")
        references = list(inputs.values())
        for run in runs:
            item = require_object(run, "run")
            references.extend((item["output"], item["candidate"]))

        for reference in references:
            item = require_object(reference, "reference")
            path = ROOT / str(item["path"])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item["sha256"])

        verifier = load_object(VERIFIER)
        for candidate in require_list(verifier["candidates"], "candidates"):
            item = require_object(candidate, "candidate")
            path = ROOT / str(item["path"])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item["sha256"])

    def test_evaluation_reports_evidence_difference_without_overclaiming_functional_gain(self) -> None:
        evaluation = load_object(EVALUATION)
        comparison = require_object(evaluation["comparison"], "comparison")
        runs = require_object(evaluation["runs"], "runs")
        baseline = require_object(runs["baseline"], "baseline")
        guided = require_object(runs["skill_guided"], "skill_guided")

        self.assertEqual(comparison["functional_repair_delta"], 0)
        self.assertIn("not a repair-success advantage", str(comparison["conclusion"]))
        baseline_record = require_object(baseline["causal_record"], "baseline record")
        guided_record = require_object(guided["causal_record"], "guided record")
        self.assertFalse(baseline_record["counterfactual"])
        self.assertTrue(guided_record["counterfactual"])
        self.assertEqual(guided_record["conclusion"], "unknown_pending_intervention")

    def test_guided_transcript_contains_causal_full_evidence(self) -> None:
        baseline = (ROOT / "examples" / "causal-probe-baseline-output.md").read_text(encoding="utf-8")
        guided = (ROOT / "examples" / "causal-probe-guided-output.md").read_text(encoding="utf-8")
        for label in ("alternative hypotheses", "timeline", "causal owner", "counterfactual intervention"):
            with self.subTest(label=label):
                self.assertIn(label, guided.lower())
        self.assertIn("counterfactual actual result: unrun", guided.lower())
        self.assertIn("unknown until the counterfactual", guided.lower())
        self.assertNotIn("counterfactual intervention", baseline.lower())


if __name__ == "__main__":
    _ = unittest.main()
