from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from typing import cast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
PLANNED_EXPERIMENT = ROOT / "examples" / "skill-effect-preregistration.json"
sys.path.insert(0, str(SCRIPTS))

from analyze_skill_effect import ExperimentError, analyze_experiment, canonical_sha256, immutable_envelope, skill_first_for  # noqa: E402


def make_completed_experiment(*, skill_repair_pass: bool, repeated_pairs: int = 1) -> dict[str, object]:
    task_strata = [*("single-module",) * 8, *("cross-module",) * 8, *("integration",) * 4]
    protocol: dict[str, object] = {
        "corpus_manifest_sha256": "a" * 64,
        "hidden_scorer_sha256": "b" * 64,
        "baseline_prompt_sha256": "c" * 64,
        "skill_prompt_sha256": "d" * 64,
        "pairing": "same task, randomized condition order",
        "hidden_scorer_blind_to_condition": True,
    }
    experiment: dict[str, object] = {
        "schema_version": 1,
        "experiment_id": "synthetic-skill-effect",
        "status": "completed",
        "scope": {
            "claim": "Synthetic test fixture only.",
            "model_id": "fixed-model",
            "harness_id": "fixed-harness",
            "skill_revision_sha256": "f" * 64,
        },
        "preregistration": {
            "git_commit": "e" * 40,
            "recorded_before_first_trial": True,
            "protocol_sha256": canonical_sha256(protocol),
            "envelope_sha256": "pending",
        },
        "protocol": protocol,
        "analysis": {
            "alpha": 0.05,
            "bootstrap_resamples": 1000,
            "permutation_resamples": 10000,
            "random_seed": 23,
            "minimum_effect": 0.05,
            "minimum_distinct_tasks": 20,
            "stratum_weights": {"single-module": 0.4, "cross-module": 0.4, "integration": 0.2},
        },
        "task_plan": {
            "tasks": [
                {"task_id": f"task-{task_index}", "stratum": stratum}
                for task_index, stratum in enumerate(task_strata)
            ]
        },
        "stopping_rule": {
            "kind": "fixed_complete_pairs",
            "pairs_per_task": repeated_pairs,
            "early_stop": "not allowed",
        },
        "trials": [],
    }
    preregistration = cast(dict[str, object], experiment["preregistration"])
    preregistration["envelope_sha256"] = canonical_sha256(immutable_envelope(experiment))
    trials: list[dict[str, object]] = []
    experiment["trials"] = trials
    for task_index, stratum in enumerate(task_strata):
        for repetition in range(repeated_pairs):
            pair_id = f"task-{task_index}-run-{repetition}"
            replicate_index = repetition + 1
            first_is_skill = skill_first_for(23, f"task-{task_index}", replicate_index)
            trials.extend(
                [
                    {
                        "pair_id": pair_id,
                        "task_id": f"task-{task_index}",
                        "stratum": stratum,
                        "condition": "skill" if first_is_skill else "baseline",
                        "execution_order": 1,
                        "replicate_index": replicate_index,
                        "model_id": "fixed-model",
                        "harness_id": "fixed-harness",
                        "hidden_repair_pass": skill_repair_pass if first_is_skill else False,
                    },
                    {
                        "pair_id": pair_id,
                        "task_id": f"task-{task_index}",
                        "stratum": stratum,
                        "condition": "baseline" if first_is_skill else "skill",
                        "execution_order": 2,
                        "replicate_index": replicate_index,
                        "model_id": "fixed-model",
                        "harness_id": "fixed-harness",
                        "hidden_repair_pass": False if first_is_skill else skill_repair_pass,
                    },
                ]
            )
    return experiment


class SkillEffectAnalysisTests(unittest.TestCase):
    def test_planned_preregistration_is_not_mistaken_for_evidence(self) -> None:
        planned = cast(object, json.loads(PLANNED_EXPERIMENT.read_text(encoding="utf-8")))
        assert isinstance(planned, dict)
        report = analyze_experiment(cast(dict[str, object], planned))
        self.assertEqual(report["status"], "planned")
        self.assertEqual(report["primary_metric"]["decision"], "not_measured")
        self.assertIn("not evidence", report["conclusion"])

    def test_clear_positive_paired_effect_meets_the_preregistered_gate(self) -> None:
        report = analyze_experiment(make_completed_experiment(skill_repair_pass=True))
        primary = report["primary_metric"]
        self.assertEqual(primary["decision"], "improved")
        self.assertEqual(primary["distinct_tasks"], 20)
        self.assertEqual(primary["paired_runs"], 20)
        self.assertEqual(primary["effect"], 1.0)
        interval = primary["confidence_interval_95"]
        p_value = primary["one_sided_randomization_p_value"]
        assert interval is not None
        assert p_value is not None
        self.assertGreater(interval[0], 0.05)
        self.assertLess(p_value, 0.05)
        self.assertIn("preregistered model", report["conclusion"])

    def test_no_effect_is_not_promoted_to_improved(self) -> None:
        report = analyze_experiment(make_completed_experiment(skill_repair_pass=False))
        primary = report["primary_metric"]
        self.assertEqual(primary["decision"], "no_demonstrated_improvement")
        self.assertEqual(primary["effect"], 0.0)
        self.assertIn("no scoped repair-success improvement", report["conclusion"])

    def test_insufficient_held_out_tasks_is_inconclusive_even_with_a_positive_effect(self) -> None:
        experiment = make_completed_experiment(skill_repair_pass=False)
        trials = cast(list[dict[str, object]], experiment["trials"])
        for index, trial in enumerate(trials):
            if trial["task_id"] == "task-0" and trial["condition"] == "skill":
                trials[index] = {**trial, "hidden_repair_pass": True}
        report = analyze_experiment(experiment)
        primary = report["primary_metric"]
        self.assertEqual(primary["decision"], "inconclusive")
        self.assertTrue(primary["eligible"])

    def test_repeated_runs_are_clustered_by_task_not_counted_as_independent_tasks(self) -> None:
        report = analyze_experiment(make_completed_experiment(skill_repair_pass=True, repeated_pairs=2))
        primary = report["primary_metric"]
        self.assertEqual(primary["distinct_tasks"], 20)
        self.assertEqual(primary["paired_runs"], 40)

    def test_malformed_or_unpaired_trial_data_is_rejected(self) -> None:
        experiment = make_completed_experiment(skill_repair_pass=True)
        trials = cast(list[dict[str, object]], experiment["trials"])
        _ = trials.pop()
        with self.assertRaisesRegex(ExperimentError, "exactly one baseline and one skill"):
            _ = analyze_experiment(experiment)

    def test_missing_stratum_and_nonrandomized_condition_order_are_rejected(self) -> None:
        with self.subTest("missing stratum"):
            experiment = make_completed_experiment(skill_repair_pass=True)
            trials = cast(list[dict[str, object]], experiment["trials"])
            _ = experiment["trials"] = [
                trial for trial in trials if trial["stratum"] != "integration"
            ]
            with self.assertRaisesRegex(ExperimentError, "include every preregistered task"):
                _ = analyze_experiment(experiment)
        with self.subTest("condition order"):
            experiment = make_completed_experiment(skill_repair_pass=True)
            trials = cast(list[dict[str, object]], experiment["trials"])
            for index, trial in enumerate(trials):
                if trial["condition"] == "skill":
                    trials[index] = {**trial, "execution_order": 1}
                else:
                    trials[index] = {**trial, "execution_order": 2}
            with self.assertRaisesRegex(ExperimentError, "does not match the preregistered randomized condition order"):
                _ = analyze_experiment(experiment)

    def test_protocol_digest_and_model_drift_are_rejected(self) -> None:
        with self.subTest("digest"):
            experiment = make_completed_experiment(skill_repair_pass=True)
            preregistration = experiment["preregistration"]
            assert isinstance(preregistration, dict)
            preregistration["protocol_sha256"] = "0" * 64
            with self.assertRaisesRegex(ExperimentError, "does not match protocol"):
                _ = analyze_experiment(experiment)
        with self.subTest("model"):
            experiment = make_completed_experiment(skill_repair_pass=True)
            trials = cast(list[dict[str, object]], experiment["trials"])
            trials[0] = {**trials[0], "model_id": "different-model"}
            with self.assertRaisesRegex(ExperimentError, "differs from scope.model_id"):
                _ = analyze_experiment(experiment)
        with self.subTest("envelope"):
            experiment = make_completed_experiment(skill_repair_pass=True)
            analysis = cast(dict[str, object], experiment["analysis"])
            analysis["minimum_distinct_tasks"] = 2
            with self.assertRaisesRegex(ExperimentError, "does not match the immutable preregistration envelope"):
                _ = analyze_experiment(experiment)

    def test_cli_can_gate_on_an_improvement_decision(self) -> None:
        experiment = make_completed_experiment(skill_repair_pass=False)
        with tempfile.TemporaryDirectory() as directory_name:
            experiment_path = Path(directory_name) / "experiment.json"
            _ = experiment_path.write_text(json.dumps(experiment), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "analyze_skill_effect.py"), str(experiment_path), "--require-improvement"],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("no_demonstrated_improvement", result.stdout)


if __name__ == "__main__":
    _ = unittest.main()
