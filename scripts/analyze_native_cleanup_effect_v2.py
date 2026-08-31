#!/usr/bin/env python3
"""Analyze one complete, preregistered V2 native cleanup-effect collection."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
from typing import Any, cast

from create_native_cleanup_effect_preregistration_v2 import ROOT, canonical_sha256, immutable_envelope


CONDITIONS = ("no_skill", "old_skill", "new_skill")
REQUIRED_ARTIFACTS = ("prepare.json", "seed.txt", "candidate.diff", "agent-result.json", "score.json")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_object(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return cast(dict[str, object], value)


def required_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be non-empty text")
    return value


def required_bool(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be boolean")
    return value


def validate_preregistration(preregistration: dict[str, object], *, root: Path) -> list[dict[str, object]]:
    if preregistration.get("schema_version") != 2 or preregistration.get("status") != "planned":
        raise ValueError("V2 preregistration must be a planned schema_version 2 record")
    if preregistration.get("trials") != []:
        raise ValueError("V2 preregistration must not contain trial outcomes")
    protocol = preregistration.get("protocol")
    task_plan = preregistration.get("task_plan")
    metadata = preregistration.get("preregistration")
    if not isinstance(protocol, dict) or not isinstance(task_plan, dict) or not isinstance(metadata, dict):
        raise ValueError("V2 preregistration is missing protocol, task_plan, or metadata")
    if protocol.get("conditions") != list(CONDITIONS):
        raise ValueError("V2 preregistration conditions differ from the analyzer conditions")
    for name in ("corpus_manifest", "generator", "runner", "analyzer", "preregistration_generator", "task_prompt", "old_skill", "new_skill"):
        relative = required_text(protocol.get(f"{name}_path"), f"protocol.{name}_path")
        expected = required_text(protocol.get(f"{name}_sha256"), f"protocol.{name}_sha256")
        actual = file_sha256(root / relative)
        if actual != expected:
            raise ValueError(f"protocol.{name}_sha256 does not match the frozen input")
    if required_text(metadata.get("protocol_sha256"), "preregistration.protocol_sha256") != canonical_sha256(protocol):
        raise ValueError("preregistration.protocol_sha256 does not match protocol")
    if required_text(metadata.get("envelope_sha256"), "preregistration.envelope_sha256") != canonical_sha256(immutable_envelope(preregistration)):
        raise ValueError("preregistration.envelope_sha256 does not match immutable envelope")
    tasks = task_plan.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("task_plan.tasks must be a non-empty list")
    parsed: list[dict[str, object]] = []
    seen: set[str] = set()
    for index, raw in enumerate(tasks):
        if not isinstance(raw, dict):
            raise ValueError(f"task_plan.tasks[{index}] must be an object")
        task_id = required_text(raw.get("task_id"), f"task_plan.tasks[{index}].task_id")
        if task_id in seen:
            raise ValueError("task_plan task IDs must be unique")
        seen.add(task_id)
        if raw.get("execution_order") not in [list(permutation) for permutation in itertools.permutations(CONDITIONS)]:
            raise ValueError(f"task {task_id} has an invalid three-condition execution order")
        _ = required_text(raw.get("cohort"), f"task_plan.tasks[{index}].cohort")
        _ = required_text(raw.get("stratum"), f"task_plan.tasks[{index}].stratum")
        parsed.append(cast(dict[str, object], raw))
    return parsed


def exact_one_sided_sign_flip(values: list[int]) -> float:
    nonzero = [value for value in values if value != 0]
    if not nonzero:
        return 1.0
    observed = sum(nonzero)
    extreme = 0
    total = 0
    for signs in itertools.product((-1, 1), repeat=len(nonzero)):
        if sum(sign * abs(value) for sign, value in zip(signs, nonzero)) >= observed:
            extreme += 1
        total += 1
    return extreme / total


def load_trial(raw_root: Path, *, task_id: str, condition: str) -> dict[str, object]:
    directory = raw_root / task_id / condition
    missing = [name for name in REQUIRED_ARTIFACTS if not (directory / name).is_file()]
    if missing:
        raise ValueError(f"trial {task_id}/{condition} is missing required artifacts: {', '.join(missing)}")
    unexpected = sorted(path.name for path in directory.iterdir() if path.name not in REQUIRED_ARTIFACTS)
    if unexpected:
        raise ValueError(f"trial {task_id}/{condition} has unexpected artifacts: {', '.join(unexpected)}")
    score = load_object(directory / "score.json")
    if score.get("task_id") != task_id:
        raise ValueError(f"trial {task_id}/{condition} score task ID mismatch")
    public = score.get("public_result")
    if not isinstance(public, dict):
        raise ValueError(f"trial {task_id}/{condition} score lacks public_result")
    complete = (
        required_bool(score.get("implementation_integrity_passed"), f"{task_id}/{condition}.implementation_integrity_passed")
        and required_bool(public.get("passed"), f"{task_id}/{condition}.public_result.passed")
        and required_bool(score.get("hidden_injected_after_agent_exit"), f"{task_id}/{condition}.hidden_injected_after_agent_exit")
    )
    return {
        "task_id": task_id,
        "condition": condition,
        "complete": complete,
        "hidden_repair_pass": required_bool(score.get("hidden_repair_passed"), f"{task_id}/{condition}.hidden_repair_passed"),
        "artifact_sha256": {name: file_sha256(directory / name) for name in REQUIRED_ARTIFACTS},
    }


def analyze(preregistration: dict[str, object], raw_root: Path, *, root: Path = ROOT) -> dict[str, object]:
    tasks = validate_preregistration(preregistration, root=root.resolve())
    trials: list[dict[str, object]] = []
    errors: list[str] = []
    expected_directories = {
        (cast(str, task["task_id"]), condition)
        for task in tasks
        for condition in cast(list[str], task["execution_order"])
    }
    observed_directories = {
        (task_directory.name, condition_directory.name)
        for task_directory in raw_root.iterdir()
        if task_directory.is_dir()
        for condition_directory in task_directory.iterdir()
        if condition_directory.is_dir()
    }
    extras = sorted(observed_directories - expected_directories)
    if extras:
        errors.append("raw collection has unexpected trial directories: " + ", ".join(f"{task}/{condition}" for task, condition in extras))
    for task in tasks:
        task_id = cast(str, task["task_id"])
        for condition in cast(list[str], task["execution_order"]):
            try:
                trial = load_trial(raw_root, task_id=task_id, condition=condition)
                trial["cohort"] = task["cohort"]
                trial["stratum"] = task["stratum"]
                trial["execution_order"] = cast(list[str], task["execution_order"]).index(condition) + 1
                trials.append(trial)
                if not bool(trial["complete"]):
                    errors.append(f"trial {task_id}/{condition} failed a preregistered completion gate")
            except ValueError as error:
                errors.append(str(error))
    expected_trial_count = len(tasks) * len(CONDITIONS)
    if len(trials) != expected_trial_count:
        errors.append(f"collection has {len(trials)} readable trials, expected {expected_trial_count}")
    by_task: dict[str, dict[str, dict[str, object]]] = {}
    for trial in trials:
        by_task.setdefault(cast(str, trial["task_id"]), {})[cast(str, trial["condition"])] = trial
    primary_differences: list[int] = []
    secondary_differences: list[int] = []
    decision_regressions: list[str] = []
    for task in tasks:
        task_id = cast(str, task["task_id"])
        conditions = by_task.get(task_id, {})
        if set(conditions) != set(CONDITIONS):
            continue
        new = bool(conditions["new_skill"]["hidden_repair_pass"])
        old = bool(conditions["old_skill"]["hidden_repair_pass"])
        no_skill = bool(conditions["no_skill"]["hidden_repair_pass"])
        primary_differences.append(int(new) - int(old))
        secondary_differences.append(int(new) - int(no_skill))
        if task["cohort"] == "decision-retention" and old and not new:
            decision_regressions.append(task_id)
    complete = not errors and all(bool(trial["complete"]) for trial in trials)
    primary_effect = sum(primary_differences) / len(primary_differences) if primary_differences else None
    secondary_effect = sum(secondary_differences) / len(secondary_differences) if secondary_differences else None
    primary_p = exact_one_sided_sign_flip(primary_differences) if primary_differences else None
    analysis = cast(dict[str, object], preregistration["analysis"])
    demonstrated = bool(
        complete
        and primary_effect is not None
        and secondary_effect is not None
        and primary_p is not None
        and primary_effect >= analysis["minimum_effect"]
        and primary_p <= analysis["alpha"]
        and secondary_effect >= 0
        and not decision_regressions
    )
    return {
        "schema_version": 1,
        "experiment_id": preregistration["experiment_id"],
        "status": "completed" if complete else "ineligible",
        "analysis_eligibility": "eligible" if complete else "ineligible",
        "preregistration_sha256": canonical_sha256(preregistration),
        "collection": {
            "planned_trials": expected_trial_count,
            "completed_trials": len(trials),
            "all_implementation_integrity_and_public_checks_passed": complete,
            "all_hidden_tests_injected_after_agent_exit": complete,
            "errors": errors,
        },
        "trials": trials,
        "statistics": {
            "primary_new_skill_minus_old_skill": {
                "effect": primary_effect,
                "one_sided_exact_sign_flip_p_value": primary_p,
                "task_differences": primary_differences,
            },
            "secondary_new_skill_minus_no_skill": {
                "effect": secondary_effect,
                "task_differences": secondary_differences,
            },
            "decision_retention_regressions": decision_regressions,
        },
        "conclusion": (
            "demonstrated_improvement: within the fixed model, Harness, V2 corpus, frozen Skill snapshots, and scorer."
            if demonstrated
            else "no_demonstrated_improvement: this collection does not satisfy the preregistered V2 claim rule."
            if complete
            else "ineligible: collection did not satisfy the preregistered completeness and integrity rule."
        ),
        "limitations": [
            "This is protocol isolation on a shared filesystem, not OS or container isolation.",
            "The result cannot establish a model-wide causal-reasoning capability or production reliability claim.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("--preregistration", type=Path, required=True)
    _ = parser.add_argument("--raw-root", type=Path, required=True)
    _ = parser.add_argument("--output", type=Path, required=True)
    _ = parser.add_argument("--root", type=Path, default=ROOT)
    arguments = parser.parse_args()
    if arguments.output.exists():
        raise FileExistsError(f"refusing to overwrite analysis output: {arguments.output}")
    record = analyze(load_object(arguments.preregistration), arguments.raw_root, root=arguments.root)
    arguments.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0 if record["analysis_eligibility"] == "eligible" else 1


if __name__ == "__main__":
    raise SystemExit(main())
