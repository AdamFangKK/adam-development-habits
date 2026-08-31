from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from typing import cast


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_skill_effect_v9 import (  # noqa: E402
    CONDITIONS,
    ExperimentError,
    analyze_experiment,
    balanced_condition_order,
    condition_order,
)


def experiment(outcomes: dict[str, tuple[bool, bool, bool]]) -> dict[str, object]:
    tasks: list[dict[str, object]] = []
    trials: list[dict[str, object]] = []
    strata = ("single-module", "cross-module", "integration")
    for index, (task_id, values) in enumerate(outcomes.items()):
        cohort = "decision-retention" if index < len(outcomes) // 2 else "repair"
        stratum = strata[index % len(strata)]
        order = balanced_condition_order(17, index)
        tasks.append({"task_id": task_id, "cohort": cohort, "stratum": stratum, "execution_order": list(order)})
        by_condition = cast(dict[str, bool], dict(zip(CONDITIONS, values)))
        for execution_order, condition in enumerate(order, start=1):
            trials.append({
                "block_id": f"{task_id}-run-1",
                "task_id": task_id,
                "cohort": cohort,
                "stratum": stratum,
                "replicate_index": 1,
                "condition": condition,
                "execution_order": execution_order,
                "model_id": "model",
                "harness_id": "harness",
                "trial_complete": True,
                "implementation_integrity_passed": True,
                "hidden_repair_pass": by_condition[condition],
            })
    result = {
        "schema_version": 2,
        "experiment_id": "test-v9",
        "status": "completed",
        "scope": {"model_id": "model", "harness_id": "harness"},
        "analysis": {
            "alpha": 0.05,
            "bootstrap_resamples": 1000,
            "permutation_resamples": 10000,
            "random_seed": 17,
            "minimum_effect": 0.05,
            "minimum_tasks_per_cohort": 6,
            "stratum_weights": {"single-module": 1 / 3, "cross-module": 1 / 3, "integration": 1 / 3},
            "critical_safety_task_ids": list(outcomes)[: len(outcomes) // 2],
        },
        "task_plan": {"tasks": tasks},
        "trials": trials,
        "collection": {"isolation_audit_passed": True},
        "protocol": {},
        "stopping_rule": {},
        "preregistration": {"envelope_sha256": "pending"},
    }
    from analyze_skill_effect_v9 import canonical_sha256

    preregistration = cast(dict[str, object], result["preregistration"])
    preregistration["envelope_sha256"] = canonical_sha256({
        field: cast(dict[str, object], result[field]) for field in ("scope", "protocol", "analysis", "task_plan", "stopping_rule")
    })
    return cast(dict[str, object], result)


class EffectAnalyzerV9Tests(unittest.TestCase):
    def test_reports_improvement_only_when_both_cohorts_clear_the_gate(self) -> None:
        values = {f"task-{index:02d}": (False, False, True) for index in range(12)}
        payload = experiment(values)
        self.assertEqual(
            cast(list[str], cast(dict[str, object], payload["analysis"])["critical_safety_task_ids"]),
            [f"task-{index:02d}" for index in range(6)],
        )
        report = cast(dict[str, object], analyze_experiment(payload))
        self.assertEqual(report["decision"], "improved")
        self.assertEqual(cast(list[str], report["critical_safety_regressions"]), [])
        self.assertEqual(
            [cast(dict[str, object], item)["decision"] for item in cast(list[dict[str, object]], report["primary_contrast"])],
            ["improved", "improved"],
        )

    def test_rejects_missing_conditions_and_order_drift(self) -> None:
        values = {f"task-{index:02d}": (False, False, True) for index in range(12)}
        missing = experiment(values)
        missing_trials = cast(list[dict[str, object]], missing["trials"])
        missing["trials"] = missing_trials[:-1]
        with self.assertRaisesRegex(ExperimentError, "exactly three"):
            _ = analyze_experiment(missing)

        drifted = experiment(values)
        trials = cast(list[dict[str, object]], drifted["trials"])
        first = trials[0]
        second = trials[1]
        first["execution_order"], second["execution_order"] = second["execution_order"], first["execution_order"]
        with self.assertRaisesRegex(ExperimentError, "preregistered order"):
            _ = analyze_experiment(drifted)

    def test_rejects_failed_isolation_and_detects_safety_regression(self) -> None:
        values = {f"task-{index:02d}": (False, False, True) for index in range(12)}
        unsafe = experiment(values)
        trials = cast(list[dict[str, object]], unsafe["trials"])
        for trial in trials:
            if trial["task_id"] == "task-00" and trial["condition"] == "old_skill":
                trial["hidden_repair_pass"] = True
            if trial["task_id"] == "task-00" and trial["condition"] == "new_skill":
                trial["hidden_repair_pass"] = False
        report = cast(dict[str, object], analyze_experiment(unsafe))
        self.assertEqual(report["decision"], "not_improved")
        self.assertEqual(cast(list[str], report["critical_safety_regressions"]), ["task-00"])

        failed_audit = copy.deepcopy(unsafe)
        cast(dict[str, object], failed_audit["collection"])["isolation_audit_passed"] = False
        with self.assertRaisesRegex(ExperimentError, "isolation audit"):
            _ = analyze_experiment(failed_audit)

    def test_requires_both_cohorts_when_repair_is_missing(self) -> None:
        values = {f"task-{index:02d}": (False, False, True) for index in range(12)}
        missing_repair = experiment(values)
        task_plan = cast(dict[str, object], missing_repair["task_plan"])
        task_plan["tasks"] = cast(list[dict[str, object]], task_plan["tasks"])[:6]
        missing_repair["trials"] = [
            trial for trial in cast(list[dict[str, object]], missing_repair["trials"])
            if cast(str, trial["cohort"]) != "repair"
        ]
        missing_repair["preregistration"] = {
            "envelope_sha256": "placeholder",
        }
        from analyze_skill_effect_v9 import canonical_sha256

        preregistration = cast(dict[str, object], missing_repair["preregistration"])
        preregistration["envelope_sha256"] = canonical_sha256({
            field: cast(dict[str, object], missing_repair[field])
            for field in ("scope", "protocol", "analysis", "task_plan", "stopping_rule")
        })
        with self.assertRaisesRegex(ExperimentError, "requires cohorts"):
            _ = analyze_experiment(missing_repair)


if __name__ == "__main__":
    _ = unittest.main()
