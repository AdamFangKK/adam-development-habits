"""Ensure the V8 preregistration locks the isolation-aware protocol."""

# pyright: reportMissingTypeStubs=false

from __future__ import annotations

import hashlib
import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from typing import cast


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import run_effect_experiment_v6 as v6  # noqa: E402
import run_effect_experiment_v8 as v8  # noqa: E402
from analyze_skill_effect import ExperimentError, analyze_experiment, canonical_sha256, immutable_envelope  # noqa: E402


def load_object(path: Path) -> dict[str, object]:
    value = cast(object, json.loads(path.read_text(encoding="utf-8")))
    if not isinstance(value, dict):
        raise AssertionError(f"{path} must contain a JSON object")
    return cast(dict[str, object], value)


class EffectExperimentV8Tests(unittest.TestCase):
    def test_preregistration_freezes_fresh_corpus_and_isolation_components(self) -> None:
        preregistration = load_object(ROOT / "examples" / "effect-experiment-v8" / "preregistration.json")
        manifest = load_object(ROOT / "examples" / "effect-corpus-v8" / "manifest.json")
        protocol = cast(dict[str, object], preregistration["protocol"])
        metadata = cast(dict[str, object], preregistration["preregistration"])
        report = analyze_experiment(preregistration)

        self.assertEqual(preregistration["status"], "planned")
        self.assertEqual(preregistration["trials"], [])
        self.assertEqual(report["conclusion"], "not_run: this preregistration is a protocol, not evidence that the Skill improves a model.")
        self.assertEqual(protocol["runner_sha256"], hashlib.sha256((SCRIPTS / "run_effect_experiment_v8.py").read_bytes()).hexdigest())
        self.assertEqual(protocol["hidden_scorer_sha256"], hashlib.sha256((SCRIPTS / "score_effect_workspace_v8.py").read_bytes()).hexdigest())
        self.assertEqual(protocol["isolation_auditor_sha256"], hashlib.sha256((SCRIPTS / "audit_effect_isolation_v8.py").read_bytes()).hexdigest())
        self.assertEqual(protocol["codex_wrapper_sha256"], hashlib.sha256((SCRIPTS / "codex_v8_isolated.py").read_bytes()).hexdigest())
        self.assertEqual(protocol["generator_sha256"], hashlib.sha256((SCRIPTS / "materialize_effect_corpus_v8.py").read_bytes()).hexdigest())
        self.assertEqual(protocol["corpus_manifest_sha256"], hashlib.sha256((ROOT / "examples" / "effect-corpus-v8" / "manifest.json").read_bytes()).hexdigest())
        self.assertTrue(bool(protocol["skill_search_disabled_for_both_conditions"]))
        self.assertTrue(bool(protocol["treatment_requires_snapshot_read_evidence"]))
        self.assertEqual(metadata["protocol_sha256"], canonical_sha256(protocol))
        self.assertEqual(metadata["envelope_sha256"], canonical_sha256(immutable_envelope(preregistration)))

        records = v6.records_for_preregistration(manifest, preregistration)
        self.assertEqual(len(records), 20)
        self.assertEqual(v8.DEFAULT_HARNESS_ID, cast(dict[str, object], preregistration["scope"])["harness_id"])

    def test_completed_v8_result_requires_a_durable_passed_isolation_audit(self) -> None:
        experiment = deepcopy(load_object(ROOT / "examples" / "effect-experiment-v4" / "completed.json"))
        scope = cast(dict[str, object], experiment["scope"])
        scope["harness_id"] = v8.DEFAULT_HARNESS_ID
        for trial_value in cast(list[object], experiment["trials"]):
            trial = cast(dict[str, object], trial_value)
            trial["harness_id"] = v8.DEFAULT_HARNESS_ID
        metadata = cast(dict[str, object], experiment["preregistration"])
        metadata["envelope_sha256"] = canonical_sha256(immutable_envelope(experiment))
        experiment["collection"] = {}

        with self.assertRaisesRegex(ExperimentError, "passed isolation audit"):
            _ = analyze_experiment(experiment)

        experiment["collection"] = {"isolation_audit_passed": True, "isolation_audit": {"passed": True}}
        self.assertIn("conclusion", analyze_experiment(experiment))


if __name__ == "__main__":
    _ = unittest.main()
