from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path
from typing import cast


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "examples" / "external-quixbugs-run-manifest.json"
EVALUATION = ROOT / "examples" / "external-quixbugs-evaluation.json"
BASELINE = ROOT / "examples" / "external-quixbugs-baseline-output.md"
GUIDED = ROOT / "examples" / "external-quixbugs-skill-output.md"
BASELINE_DIFF = ROOT / "examples" / "external-quixbugs-baseline.diff"
GUIDED_DIFF = ROOT / "examples" / "external-quixbugs-skill.diff"
HIDDEN_CHECK = ROOT / "examples" / "external-quixbugs-hidden-check.py"
VERIFIER_REPORT = ROOT / "examples" / "external-quixbugs-verifier-report.json"
EVIDENCE = ROOT / ".adam" / "evidence" / "external-quixbugs-benchmark.json"
VALIDATOR = ROOT / "scripts" / "validate_evidence.py"


def load_object(path: Path) -> dict[str, object]:
    value = normalize_json(cast(object, json.loads(path.read_text(encoding="utf-8"))))
    return require_object(value, str(path))


def normalize_json(value: object) -> object:
    if isinstance(value, dict):
        normalized: dict[str, object] = {}
        for key, item in cast(dict[object, object], value).items():
            if not isinstance(key, str):
                raise AssertionError("JSON object keys must be text")
            normalized[key] = normalize_json(item)
        return normalized
    if isinstance(value, list):
        return [normalize_json(item) for item in cast(list[object], value)]
    if value is None or isinstance(value, (bool, float, int, str)):
        return value
    raise AssertionError("JSON must contain only standard JSON values")


def require_object(value: object, name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise AssertionError(f"{name} must be an object")
    return cast(dict[str, object], value)


def require_text(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise AssertionError(f"{name} must be text")
    return value


def require_bool(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise AssertionError(f"{name} must be boolean")
    return value


def require_list(value: object, name: str) -> list[object]:
    if not isinstance(value, list):
        raise AssertionError(f"{name} must be a list")
    return cast(list[object], value)


class ExternalQuixBugsBenchmarkTests(unittest.TestCase):
    def test_manifest_pins_source_and_excludes_the_gold_implementation(self) -> None:
        manifest = load_object(MANIFEST)
        source = require_object(manifest["source"], "source")
        protocol = require_object(manifest["protocol"], "protocol")
        repair_boundary = require_object(protocol["repair_agent_boundary"], "repair_agent_boundary")
        verifier_boundary = require_object(protocol["verifier_boundary"], "verifier_boundary")
        self.assertEqual(require_text(source["repository"], "source.repository"), "https://github.com/jkoppel/QuixBugs")
        self.assertEqual(require_text(source["revision"], "source.revision"), "4257f44b0ff1181dedaedee6a447e133219fcebf")
        self.assertIn("correct_python_programs/", require_list(repair_boundary["excluded_from_fixture"], "excluded_from_fixture"))
        self.assertIn("rather than proof of filesystem isolation", require_text(protocol["assurance"], "assurance"))
        self.assertEqual(require_text(verifier_boundary["timing"], "verifier timing"), "after both repair agents completed")

    def test_saved_outputs_and_evaluation_preserve_the_observed_comparison(self) -> None:
        evaluation = load_object(EVALUATION)
        pre_repair = require_object(evaluation["pre_repair"], "pre_repair")
        runs = require_object(evaluation["runs"], "runs")
        baseline = require_object(runs["baseline"], "baseline")
        guided = require_object(runs["skill_guided"], "skill_guided")
        comparison = require_object(evaluation["comparison"], "comparison")
        self.assertEqual(require_text(evaluation["source_revision"], "source_revision"), "4257f44b0ff1181dedaedee6a447e133219fcebf")
        self.assertEqual(require_text(pre_repair["result"], "pre_repair.result"), "3 failed in 0.02s")
        self.assertEqual(require_text(baseline["result"], "baseline.result"), "passed")
        self.assertEqual(require_text(guided["result"], "guided.result"), "passed")
        self.assertEqual(comparison["functional_repair_delta"], 0)
        self.assertIn("does not show a repair-success advantage", require_text(comparison["conclusion"], "comparison.conclusion"))
        self.assertTrue(require_bool(baseline["test_and_configuration_unchanged"], "baseline unchanged"))
        self.assertTrue(require_bool(guided["test_and_configuration_unchanged"], "guided unchanged"))

    def test_diffs_and_hidden_check_remain_available_for_replay(self) -> None:
        self.assertIn("weight_by_node[v]", BASELINE_DIFF.read_text(encoding="utf-8"))
        self.assertIn("weight_by_node[v]", GUIDED_DIFF.read_text(encoding="utf-8"))
        hidden_check = HIDDEN_CHECK.read_text(encoding="utf-8")
        self.assertIn("CASES", hidden_check)
        self.assertIn("candidate mutated the input mapping", hidden_check)

    def test_verifier_report_pins_fixture_and_repair_hashes(self) -> None:
        report = load_object(VERIFIER_REPORT)
        source = require_object(report["source"], "source")
        integrity = require_object(report["repair_fixture_integrity"], "repair_fixture_integrity")
        hidden = require_object(report["hidden_differential_check"], "hidden_differential_check")
        self.assertEqual(require_text(source["original_source_sha256"], "original source"), "e99679a54634bc940a78c1f211e6126f5119a7654a089d1f56f264a1deaa0ce2")
        self.assertEqual(require_text(source["public_test_sha256"], "public test"), "8ee521556000dc6bcf4ae71c6db0f91c387f96e055557ec1accdde824928b4f8")
        self.assertEqual(require_text(source["conftest_sha256"], "conftest"), "e8325790da8f5d06af1251e724838c7c8a18d90c31ddc9d24d9f3aa57ce8")
        self.assertEqual(require_text(integrity["baseline_candidate_source_sha256"], "baseline candidate"), "57575618e1d5622c77f53596b42d8b3cc86553e83edaa24fb5eed917d1717aa0")
        self.assertEqual(require_text(integrity["skill_guided_candidate_source_sha256"], "guided candidate"), "bfb967b7551737317017c161dd082d4931427c44f8db6d6fade177162111d0b4")
        self.assertEqual(require_text(hidden["script_sha256"], "hidden script"), hashlib.sha256(HIDDEN_CHECK.read_bytes()).hexdigest())
        results = require_list(hidden["results"], "hidden results")
        self.assertEqual(len(results), 2)
        for index, result in enumerate(results):
            with self.subTest(result=index):
                item = require_object(result, "hidden result")
                self.assertEqual(item["case_count"], 2)
                self.assertTrue(require_bool(item["input_mapping_unchanged"], "input_mapping_unchanged"))
                self.assertEqual(require_text(item["result"], "hidden result"), "passed")

    def test_verifier_report_hashes_committed_artifacts(self) -> None:
        report = load_object(VERIFIER_REPORT)
        for reference in require_list(report["committed_artifacts"], "committed_artifacts"):
            item = require_object(reference, "artifact reference")
            path = ROOT / require_text(item["path"], "artifact path")
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), require_text(item["sha256"], "artifact digest"))

    def test_machine_evidence_artifact_is_valid(self) -> None:
        result = subprocess.run(
            [sys.executable, str(VALIDATOR), str(EVIDENCE)],
            capture_output=True,
            text=True,
            check=False,
            cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("valid evidence", result.stdout)

    def test_guided_output_contains_the_required_causal_lite_record(self) -> None:
        guided = GUIDED.read_text(encoding="utf-8")
        baseline = BASELINE.read_text(encoding="utf-8")
        for required in (
            "Causal Lite",
            "Observed symptom:",
            "Alternative hypothesis:",
            "Discriminating check:",
            "Invariant:",
            "Causal conclusion classification: root-cause fix.",
        ):
            with self.subTest(required=required):
                self.assertIn(required, guided)
        self.assertNotIn("Causal Lite", baseline)

    def test_output_hashes_are_stable_for_the_evidence_artifact(self) -> None:
        self.assertEqual(
            hashlib.sha256(BASELINE.read_bytes()).hexdigest(),
            "3ae901dd646811f9428303f00dac537d5e836ec3b29faa80d3963a3946b3c0ce",
        )
        self.assertEqual(
            hashlib.sha256(GUIDED.read_bytes()).hexdigest(),
            "34faeb5361f5a7e88eea4830137c0148ef4b937a0b607d15a61c4fa2b2a9ce60",
        )


if __name__ == "__main__":
    _ = unittest.main()
