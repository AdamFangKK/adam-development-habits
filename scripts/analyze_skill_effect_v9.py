#!/usr/bin/env python3
"""Analyze the preregistered three-condition V9 Skill-effect experiment."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import random
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from analyze_skill_effect import (
    bootstrap_interval,  # pyright: ignore[reportAttributeAccessIssue]
    permutation_p_value,  # pyright: ignore[reportAttributeAccessIssue]
    weighted_effect,  # pyright: ignore[reportAttributeAccessIssue]
)


CONDITIONS = ("no_skill", "old_skill", "new_skill")
PRIMARY_CONTRAST = ("new_skill", "old_skill")
SECONDARY_CONTRAST = ("new_skill", "no_skill")
EXPECTED_COHORTS = {"decision-retention", "repair"}


class ExperimentError(ValueError):
    """Raised when a V9 record cannot support its preregistered analysis."""


@dataclass(frozen=True)
class AnalysisConfig:
    alpha: float
    bootstrap_resamples: int
    permutation_resamples: int
    random_seed: int
    minimum_effect: float
    minimum_tasks_per_cohort: int
    stratum_weights: dict[str, float]


@dataclass(frozen=True)
class Block:
    task_id: str
    cohort: str
    stratum: str
    outcomes: dict[str, float]


def require_object(value: object, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ExperimentError(f"{field} must be an object")
    return cast(dict[str, object], value)


def require_list(value: object, field: str) -> list[object]:
    if not isinstance(value, list):
        raise ExperimentError(f"{field} must be a list")
    return cast(list[object], value)


def require_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ExperimentError(f"{field} must be non-empty text")
    return value


def require_bool(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise ExperimentError(f"{field} must be boolean")
    return value


def require_integer(value: object, field: str, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise ExperimentError(f"{field} must be an integer >= {minimum}")
    return value


def require_number(value: object, field: str, minimum: float, maximum: float) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ExperimentError(f"{field} must be numeric")
    number = float(value)
    if number < minimum or number > maximum:
        raise ExperimentError(f"{field} must be in [{minimum}, {maximum}]")
    return number


def condition_order(random_seed: int, task_id: str, replicate_index: int = 1) -> tuple[str, ...]:
    """Return a deterministic balanced-looking permutation without mutable RNG state."""
    ranked = sorted(
        CONDITIONS,
        key=lambda condition: hashlib.sha256(
            f"{random_seed}:{task_id}:{replicate_index}:{condition}".encode("utf-8")
        ).digest(),
    )
    return tuple(ranked)


def balanced_condition_order(random_seed: int, block_index: int) -> tuple[str, ...]:
    permutations = list(itertools.permutations(CONDITIONS))
    random.Random(random_seed).shuffle(permutations)
    return permutations[block_index % len(permutations)]


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_envelope(experiment: Mapping[str, object]) -> None:
    preregistration = require_object(experiment.get("preregistration"), "preregistration")
    expected = require_text(preregistration.get("envelope_sha256"), "preregistration.envelope_sha256")
    envelope = {
        field: require_object(experiment.get(field), field)
        for field in ("scope", "protocol", "analysis", "task_plan", "stopping_rule")
    }
    if expected != canonical_sha256(envelope):
        raise ExperimentError("preregistration envelope hash does not match the frozen protocol")


def parse_config(experiment: Mapping[str, object]) -> AnalysisConfig:
    analysis = require_object(experiment.get("analysis"), "analysis")
    weights_value = require_object(analysis.get("stratum_weights"), "analysis.stratum_weights")
    weights = {
        require_text(key, "analysis.stratum_weights key"): require_number(
            value, f"analysis.stratum_weights.{key}", 0.0, 1.0
        )
        for key, value in weights_value.items()
    }
    if not weights or abs(sum(weights.values()) - 1.0) > 1e-9:
        raise ExperimentError("analysis.stratum_weights must sum to 1")
    alpha = require_number(analysis.get("alpha"), "analysis.alpha", 0.000001, 0.5)
    return AnalysisConfig(
        alpha=alpha,
        bootstrap_resamples=require_integer(
            analysis.get("bootstrap_resamples"), "analysis.bootstrap_resamples", 1000
        ),
        permutation_resamples=require_integer(
            analysis.get("permutation_resamples"), "analysis.permutation_resamples", 10000
        ),
        random_seed=require_integer(analysis.get("random_seed"), "analysis.random_seed"),
        minimum_effect=require_number(
            analysis.get("minimum_effect"), "analysis.minimum_effect", 0.0, 1.0
        ),
        minimum_tasks_per_cohort=require_integer(
            analysis.get("minimum_tasks_per_cohort"), "analysis.minimum_tasks_per_cohort", 2
        ),
        stratum_weights=weights,
    )


def planned_tasks(experiment: Mapping[str, object]) -> dict[str, tuple[str, str, tuple[str, ...]]]:
    task_plan = require_object(experiment.get("task_plan"), "task_plan")
    planned: dict[str, tuple[str, str, tuple[str, ...]]] = {}
    for index, value in enumerate(require_list(task_plan.get("tasks"), "task_plan.tasks")):
        task = require_object(value, f"task_plan.tasks[{index}]")
        task_id = require_text(task.get("task_id"), f"task_plan.tasks[{index}].task_id")
        if task_id in planned:
            raise ExperimentError(f"duplicate planned task {task_id}")
        planned[task_id] = (
            require_text(task.get("cohort"), f"task_plan.tasks[{index}].cohort"),
            require_text(task.get("stratum"), f"task_plan.tasks[{index}].stratum"),
            tuple(
                require_text(condition, f"task_plan.tasks[{index}].execution_order item")
                for condition in require_list(
                    task.get("execution_order"), f"task_plan.tasks[{index}].execution_order"
                )
            ),
        )
        if planned[task_id][2] != balanced_condition_order(
            require_integer(require_object(experiment.get("analysis"), "analysis").get("random_seed"), "analysis.random_seed"),
            index,
        ):
            raise ExperimentError(f"task_plan.tasks[{index}].execution_order is not the balanced preregistered order")
    return planned


def parse_blocks(experiment: Mapping[str, object], config: AnalysisConfig) -> list[Block]:
    scope = require_object(experiment.get("scope"), "scope")
    model_id = require_text(scope.get("model_id"), "scope.model_id")
    harness_id = require_text(scope.get("harness_id"), "scope.harness_id")
    expected_tasks = planned_tasks(experiment)
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for index, value in enumerate(require_list(experiment.get("trials"), "trials")):
        trial = require_object(value, f"trials[{index}]")
        if require_text(trial.get("model_id"), f"trials[{index}].model_id") != model_id:
            raise ExperimentError(f"trials[{index}] model differs from scope")
        if require_text(trial.get("harness_id"), f"trials[{index}].harness_id") != harness_id:
            raise ExperimentError(f"trials[{index}] harness differs from scope")
        if not require_bool(trial.get("trial_complete"), f"trials[{index}].trial_complete"):
            raise ExperimentError(f"trials[{index}] is incomplete")
        if not require_bool(
            trial.get("implementation_integrity_passed"),
            f"trials[{index}].implementation_integrity_passed",
        ):
            raise ExperimentError(f"trials[{index}] failed implementation integrity")
        grouped[require_text(trial.get("block_id"), f"trials[{index}].block_id")].append(trial)

    blocks: list[Block] = []
    seen_tasks: set[str] = set()
    for block_id, trials in grouped.items():
        if len(trials) != len(CONDITIONS):
            raise ExperimentError(f"block {block_id} must contain exactly three trials")
        by_condition = {
            require_text(trial.get("condition"), f"block {block_id} condition"): trial
            for trial in trials
        }
        if set(by_condition) != set(CONDITIONS):
            raise ExperimentError(f"block {block_id} must contain each V9 condition once")
        task_ids = {require_text(trial.get("task_id"), f"block {block_id} task_id") for trial in trials}
        cohorts = {require_text(trial.get("cohort"), f"block {block_id} cohort") for trial in trials}
        strata = {require_text(trial.get("stratum"), f"block {block_id} stratum") for trial in trials}
        replicates = {
            require_integer(trial.get("replicate_index"), f"block {block_id} replicate_index", 1)
            for trial in trials
        }
        if len(task_ids) != 1 or len(cohorts) != 1 or len(strata) != 1 or replicates != {1}:
            raise ExperimentError(f"block {block_id} changed task, cohort, stratum, or replicate")
        task_id = next(iter(task_ids))
        cohort = next(iter(cohorts))
        stratum = next(iter(strata))
        planned = expected_tasks.get(task_id)
        if planned is None or planned[:2] != (cohort, stratum):
            raise ExperimentError(f"block {block_id} is not in the preregistered task plan")
        if task_id in seen_tasks:
            raise ExperimentError(f"task {task_id} appears in more than one block")
        seen_tasks.add(task_id)
        order = planned[2]
        actual_order = tuple(
            require_text(
                next(trial for trial in trials if trial.get("execution_order") == position).get("condition"),
                f"block {block_id} order {position}",
            )
            for position in range(1, 4)
        )
        if actual_order != order:
            raise ExperimentError(f"block {block_id} does not match the preregistered order")
        blocks.append(
            Block(
                task_id=task_id,
                cohort=cohort,
                stratum=stratum,
                outcomes={
                    condition: float(
                        require_bool(trial.get("hidden_repair_pass"), f"block {block_id} {condition} outcome")
                    )
                    for condition, trial in by_condition.items()
                },
            )
        )
    if seen_tasks != set(expected_tasks):
        missing = sorted(set(expected_tasks) - seen_tasks)
        extra = sorted(seen_tasks - set(expected_tasks))
        raise ExperimentError(f"completed blocks differ from task plan; missing={missing}, extra={extra}")
    return blocks


def contrast_report(
    blocks: list[Block],
    config: AnalysisConfig,
    cohort: str,
    contrast: tuple[str, str],
) -> dict[str, object]:
    selected = [block for block in blocks if block.cohort == cohort]
    task_values = {
        block.task_id: [block.outcomes[contrast[0]] - block.outcomes[contrast[1]]]
        for block in selected
    }
    task_strata = {block.task_id: block.stratum for block in selected}
    missing_strata = set(config.stratum_weights) - set(task_strata.values())
    if missing_strata:
        raise ExperimentError(f"cohort {cohort} is missing strata {sorted(missing_strata)}")
    effect = weighted_effect(task_values, task_strata, config.stratum_weights)
    interval = bootstrap_interval(
        task_values,
        task_strata,
        config.stratum_weights,
        alpha=config.alpha,
        resamples=config.bootstrap_resamples,
        random_seed=config.random_seed,
    )
    p_value, method = permutation_p_value(
        task_values,
        task_strata,
        config.stratum_weights,
        effect,
        resamples=config.permutation_resamples,
        random_seed=config.random_seed + 1,
    )
    enough = len(selected) >= config.minimum_tasks_per_cohort
    if enough and interval[0] > config.minimum_effect and p_value < config.alpha:
        decision = "improved"
    elif enough and interval[1] <= 0:
        decision = "no_demonstrated_improvement"
    else:
        decision = "inconclusive"
    return {
        "cohort": cohort,
        "contrast": f"{contrast[0]}-{contrast[1]}",
        "decision": decision,
        "task_count": len(selected),
        "effect": effect,
        "confidence_interval_95": interval,
        "one_sided_randomization_p_value": p_value,
        "randomization_method": method,
        "minimum_effect": config.minimum_effect,
        "alpha": config.alpha,
    }


def analyze_experiment(experiment: Mapping[str, object]) -> dict[str, object]:
    if require_integer(experiment.get("schema_version"), "schema_version", 1) != 2:
        raise ExperimentError("schema_version must be 2")
    experiment_id = require_text(experiment.get("experiment_id"), "experiment_id")
    status = require_text(experiment.get("status"), "status")
    validate_envelope(experiment)
    config = parse_config(experiment)
    if status == "planned":
        if require_list(experiment.get("trials"), "trials"):
            raise ExperimentError("planned experiments must not contain trials")
        return {
            "experiment_id": experiment_id,
            "status": "planned",
            "decision": "not_run",
            "causal_conclusion": "unknown",
            "reason": "A preregistration contains no model outcomes.",
        }
    if status != "completed":
        raise ExperimentError("only planned or completed experiments are analyzable")
    collection = require_object(experiment.get("collection"), "collection")
    if collection.get("isolation_audit_passed") is not True:
        raise ExperimentError("completed V9 analysis requires a passed isolation audit")
    blocks = parse_blocks(experiment, config)
    cohorts = {block.cohort for block in blocks}
    if cohorts != EXPECTED_COHORTS:
        raise ExperimentError(
            f"completed V9 analysis requires cohorts {sorted(EXPECTED_COHORTS)}; got {sorted(cohorts)}"
        )
    ordered_cohorts = sorted(cohorts)
    primary = [contrast_report(blocks, config, cohort, PRIMARY_CONTRAST) for cohort in ordered_cohorts]
    secondary = [contrast_report(blocks, config, cohort, SECONDARY_CONTRAST) for cohort in ordered_cohorts]
    analysis = require_object(experiment.get("analysis"), "analysis")
    critical_ids = {
        require_text(value, "analysis.critical_safety_task_ids item")
        for value in require_list(analysis.get("critical_safety_task_ids"), "analysis.critical_safety_task_ids")
    }
    expected_critical_ids = {block.task_id for block in blocks if block.cohort == "decision-retention"}
    if critical_ids != expected_critical_ids:
        raise ExperimentError("critical safety task IDs must equal the decision-retention cohort")
    regressions = sorted(
        block.task_id
        for block in blocks
        if block.task_id in critical_ids
        and block.outcomes["old_skill"] == 1.0
        and block.outcomes["new_skill"] == 0.0
    )
    primary_improved = all(report["decision"] == "improved" for report in primary)
    decision = "improved" if primary_improved and not regressions else "not_improved"
    return {
        "experiment_id": experiment_id,
        "status": "completed",
        "decision": decision,
        "causal_conclusion": (
            "Skill-conditioned capability improved within the preregistered model, harness, corpus, and scorer."
            if decision == "improved"
            else "unknown"
        ),
        "primary_contrast": primary,
        "secondary_anchor": secondary,
        "critical_safety_regressions": regressions,
        "isolation_audit_passed": True,
        "limitations": [
            "This does not establish an intrinsic model-wide capability change.",
            "The result applies only to the frozen model, Harness, Skill snapshots, corpus, and scorer.",
            "One run per task estimates task-level effects, not within-task model variance.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("experiment", type=Path)
    _ = parser.add_argument("--output", type=Path)
    _ = parser.add_argument("--require-improvement", action="store_true")
    arguments = parser.parse_args()
    value = cast(object, json.loads(arguments.experiment.read_text(encoding="utf-8")))
    report = analyze_experiment(require_object(value, str(arguments.experiment)))
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if arguments.output:
        _ = arguments.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if not arguments.require_improvement or report["decision"] == "improved" else 1


if __name__ == "__main__":
    raise SystemExit(main())
