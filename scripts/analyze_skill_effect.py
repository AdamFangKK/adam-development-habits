#!/usr/bin/env python3
"""Analyze a preregistered paired experiment of Skill-assisted repair work."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import random
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional, Protocol, TypedDict, cast


Condition = Literal["baseline", "skill"]
MetricName = Literal["hidden_repair_success", "blinded_causal_quality"]


class ExperimentError(ValueError):
    """Raised when an experiment cannot support the requested comparison."""


class MetricReport(TypedDict):
    metric: MetricName
    eligible: bool
    decision: str
    distinct_tasks: int
    paired_runs: int
    effect: float | None
    confidence_interval_95: list[float] | None
    one_sided_randomization_p_value: float | None
    randomization_method: str | None
    reason: str | None


class AnalysisReport(TypedDict):
    experiment_id: str
    status: str
    scope: dict[str, object]
    primary_metric: MetricReport
    secondary_metric: MetricReport
    conclusion: str
    limitations: list[str]


class CommandArguments(Protocol):
    experiment: Path
    output: Optional[Path]
    require_improvement: bool


@dataclass(frozen=True)
class PairObservation:
    task_id: str
    stratum: str
    repair_difference: float
    causal_difference: float | None


@dataclass(frozen=True)
class AnalysisConfig:
    alpha: float
    bootstrap_resamples: int
    permutation_resamples: int
    random_seed: int
    minimum_effect: float
    minimum_distinct_tasks: int
    stratum_weights: dict[str, float]


@dataclass(frozen=True)
class TaskPlan:
    task_strata: dict[str, str]
    pairs_per_task: int


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def immutable_envelope(experiment: Mapping[str, object]) -> dict[str, object]:
    """Return every pre-run choice that can affect eligibility or the conclusion."""
    return {
        "scope": require_object(experiment.get("scope"), "scope"),
        "protocol": require_object(experiment.get("protocol"), "protocol"),
        "analysis": require_object(experiment.get("analysis"), "analysis"),
        "task_plan": require_object(experiment.get("task_plan"), "task_plan"),
        "stopping_rule": require_object(experiment.get("stopping_rule"), "stopping_rule"),
    }


def skill_first_for(random_seed: int, task_id: str, replicate_index: int) -> bool:
    seed_material = f"{random_seed}:{task_id}:{replicate_index}".encode("utf-8")
    return hashlib.sha256(seed_material).digest()[0] % 2 == 1


def require_object(value: object, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ExperimentError(f"{field} must be an object")
    return cast(dict[str, object], value)


def require_list(value: object, field: str) -> list[object]:
    if not isinstance(value, list):
        raise ExperimentError(f"{field} must be a list")
    return cast(list[object], value)


def require_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExperimentError(f"{field} must be non-empty text")
    return value


def require_bool(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise ExperimentError(f"{field} must be boolean")
    return value


def require_integer(value: object, field: str, *, minimum: int | None = None) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ExperimentError(f"{field} must be an integer")
    if minimum is not None and value < minimum:
        raise ExperimentError(f"{field} must be at least {minimum}")
    return value


def require_probability(
    value: object,
    field: str,
    *,
    strictly_positive: bool = False,
    upper_inclusive: bool = False,
) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ExperimentError(f"{field} must be a number")
    result = float(value)
    lower_ok = result > 0 if strictly_positive else result >= 0
    upper_ok = result <= 1 if upper_inclusive else result < 1
    if not lower_ok or not upper_ok:
        bound = "in (0, 1]" if strictly_positive and upper_inclusive else "between 0 and 1" if strictly_positive else "in [0, 1]" if upper_inclusive else "in [0, 1)"
        raise ExperimentError(f"{field} must be {bound}")
    return result


def require_sha256(value: object, field: str, *, allow_pending: bool) -> str:
    result = require_text(value, field)
    if allow_pending and result == "pending":
        return result
    if len(result) != 64 or any(character not in "0123456789abcdef" for character in result.lower()):
        raise ExperimentError(f"{field} must be a lowercase SHA-256 digest or pending while planned")
    return result


def weighted_effect(task_values: Mapping[str, list[float]], task_strata: Mapping[str, str], weights: Mapping[str, float]) -> float:
    by_stratum: dict[str, list[float]] = defaultdict(list)
    for task_id, values in task_values.items():
        by_stratum[task_strata[task_id]].append(sum(values) / len(values))
    return sum(weights[stratum] * (sum(values) / len(values)) for stratum, values in by_stratum.items())


def percentile(sorted_values: Sequence[float], probability: float) -> float:
    if not sorted_values:
        raise ExperimentError("cannot calculate a percentile from no samples")
    position = probability * (len(sorted_values) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    lower_value = sorted_values[lower]
    return lower_value + (sorted_values[upper] - lower_value) * (position - lower)


def bootstrap_interval(
    task_values: Mapping[str, list[float]],
    task_strata: Mapping[str, str],
    weights: Mapping[str, float],
    *,
    alpha: float,
    resamples: int,
    random_seed: int,
) -> list[float]:
    task_ids_by_stratum: dict[str, list[str]] = defaultdict(list)
    for task_id, stratum in task_strata.items():
        task_ids_by_stratum[stratum].append(task_id)
    generator = random.Random(random_seed)
    samples: list[float] = []
    for _ in range(resamples):
        sampled_values: dict[str, list[float]] = {}
        sampled_strata: dict[str, str] = {}
        sample_index = 0
        for stratum, task_ids in task_ids_by_stratum.items():
            for task_id in (generator.choice(task_ids) for _ in task_ids):
                synthetic_task_id = f"{stratum}:{sample_index}"
                sampled_values[synthetic_task_id] = task_values[task_id]
                sampled_strata[synthetic_task_id] = stratum
                sample_index += 1
        samples.append(weighted_effect(sampled_values, sampled_strata, weights))
    samples.sort()
    return [percentile(samples, alpha / 2), percentile(samples, 1 - alpha / 2)]


def permutation_p_value(
    task_values: Mapping[str, list[float]],
    task_strata: Mapping[str, str],
    weights: Mapping[str, float],
    observed: float,
    *,
    resamples: int,
    random_seed: int,
) -> tuple[float, str]:
    task_ids = sorted(task_values)
    task_means = {task_id: sum(task_values[task_id]) / len(task_values[task_id]) for task_id in task_ids}
    task_count = len(task_ids)
    if task_count <= 16:
        comparisons = 0
        total = 0
        for signs in itertools.product((-1.0, 1.0), repeat=task_count):
            flipped = {task_id: [task_means[task_id] * sign] for task_id, sign in zip(task_ids, signs)}
            if weighted_effect(flipped, task_strata, weights) >= observed - 1e-12:
                comparisons += 1
            total += 1
        return comparisons / total, "exact paired sign-flip randomization"

    generator = random.Random(random_seed)
    comparisons = 0
    for _ in range(resamples):
        flipped = {
            task_id: [task_means[task_id] * generator.choice((-1.0, 1.0))]
            for task_id in task_ids
        }
        if weighted_effect(flipped, task_strata, weights) >= observed - 1e-12:
            comparisons += 1
    return (comparisons + 1) / (resamples + 1), "Monte Carlo paired sign-flip randomization"


def parse_config(experiment: Mapping[str, object], *, planned: bool) -> AnalysisConfig:
    protocol = require_object(experiment.get("protocol"), "protocol")
    analysis = require_object(experiment.get("analysis"), "analysis")
    preregistration = require_object(experiment.get("preregistration"), "preregistration")
    protocol_digest = require_sha256(
        preregistration.get("protocol_sha256"),
        "preregistration.protocol_sha256",
        allow_pending=planned,
    )
    envelope_digest = require_sha256(
        preregistration.get("envelope_sha256"),
        "preregistration.envelope_sha256",
        allow_pending=planned,
    )
    if protocol_digest != "pending":
        if protocol_digest != canonical_sha256(protocol):
            raise ExperimentError("preregistration.protocol_sha256 does not match protocol")
    if envelope_digest != "pending" and envelope_digest != canonical_sha256(immutable_envelope(experiment)):
        raise ExperimentError("preregistration.envelope_sha256 does not match the immutable preregistration envelope")
    if not planned:
        commit = require_text(preregistration.get("git_commit"), "preregistration.git_commit")
        if len(commit) != 40 or any(character not in "0123456789abcdef" for character in commit.lower()):
            raise ExperimentError("preregistration.git_commit must be a Git commit SHA for completed experiments")
        if not require_bool(preregistration.get("recorded_before_first_trial"), "preregistration.recorded_before_first_trial"):
            raise ExperimentError("completed experiments require preregistration.recorded_before_first_trial")

    for field in ("corpus_manifest_sha256", "hidden_scorer_sha256", "baseline_prompt_sha256", "skill_prompt_sha256"):
        _ = require_sha256(protocol.get(field), f"protocol.{field}", allow_pending=planned)
    if not planned and protocol["baseline_prompt_sha256"] == protocol["skill_prompt_sha256"]:
        raise ExperimentError("baseline and Skill prompt digests must differ")
    if require_text(protocol.get("pairing"), "protocol.pairing") != "same task, randomized condition order":
        raise ExperimentError("protocol.pairing must be same task, randomized condition order")
    if not require_bool(protocol.get("hidden_scorer_blind_to_condition"), "protocol.hidden_scorer_blind_to_condition"):
        raise ExperimentError("protocol.hidden_scorer_blind_to_condition must be true")

    weights_value = require_object(analysis.get("stratum_weights"), "analysis.stratum_weights")
    weights = {
        require_text(key, "analysis.stratum_weights key"): require_probability(
            value,
            f"analysis.stratum_weights.{key}",
            upper_inclusive=True,
        )
        for key, value in weights_value.items()
    }
    if not weights or not math.isclose(sum(weights.values()), 1.0, abs_tol=1e-9):
        raise ExperimentError("analysis.stratum_weights must be non-empty and sum to 1")
    return AnalysisConfig(
        alpha=require_probability(analysis.get("alpha"), "analysis.alpha", strictly_positive=True),
        bootstrap_resamples=require_integer(analysis.get("bootstrap_resamples"), "analysis.bootstrap_resamples", minimum=1_000),
        permutation_resamples=require_integer(analysis.get("permutation_resamples"), "analysis.permutation_resamples", minimum=10_000),
        random_seed=require_integer(analysis.get("random_seed"), "analysis.random_seed", minimum=0),
        minimum_effect=require_probability(
            analysis.get("minimum_effect"),
            "analysis.minimum_effect",
            upper_inclusive=True,
        ),
        minimum_distinct_tasks=require_integer(analysis.get("minimum_distinct_tasks"), "analysis.minimum_distinct_tasks", minimum=2),
        stratum_weights=weights,
    )


def parse_task_plan(experiment: Mapping[str, object], config: AnalysisConfig, *, planned: bool) -> TaskPlan:
    task_plan = require_object(experiment.get("task_plan"), "task_plan")
    stopping_rule = require_object(experiment.get("stopping_rule"), "stopping_rule")
    if require_text(stopping_rule.get("kind"), "stopping_rule.kind") != "fixed_complete_pairs":
        raise ExperimentError("stopping_rule.kind must be fixed_complete_pairs")
    if require_text(stopping_rule.get("early_stop"), "stopping_rule.early_stop") != "not allowed":
        raise ExperimentError("stopping_rule.early_stop must be not allowed")
    pairs_per_task = require_integer(stopping_rule.get("pairs_per_task"), "stopping_rule.pairs_per_task", minimum=1)
    task_strata: dict[str, str] = {}
    for index, raw_task in enumerate(require_list(task_plan.get("tasks"), "task_plan.tasks")):
        task = require_object(raw_task, f"task_plan.tasks[{index}]")
        task_id = require_text(task.get("task_id"), f"task_plan.tasks[{index}].task_id")
        stratum = require_text(task.get("stratum"), f"task_plan.tasks[{index}].stratum")
        if task_id in task_strata:
            raise ExperimentError(f"task_plan.tasks[{index}].task_id must be unique")
        if stratum not in config.stratum_weights:
            raise ExperimentError(f"task_plan.tasks[{index}].stratum is absent from analysis.stratum_weights")
        task_strata[task_id] = stratum
    if not planned and len(task_strata) < config.minimum_distinct_tasks:
        raise ExperimentError("task_plan.tasks must include at least analysis.minimum_distinct_tasks tasks")
    return TaskPlan(task_strata=task_strata, pairs_per_task=pairs_per_task)


def parse_pair_observations(
    experiment: Mapping[str, object],
    config: AnalysisConfig,
    task_plan: TaskPlan,
) -> list[PairObservation]:
    scope = require_object(experiment.get("scope"), "scope")
    model_id = require_text(scope.get("model_id"), "scope.model_id")
    harness_id = require_text(scope.get("harness_id"), "scope.harness_id")
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for index, raw_trial in enumerate(require_list(experiment.get("trials"), "trials")):
        trial = require_object(raw_trial, f"trials[{index}]")
        pair_id = require_text(trial.get("pair_id"), f"trials[{index}].pair_id")
        condition = require_text(trial.get("condition"), f"trials[{index}].condition")
        if condition not in ("baseline", "skill"):
            raise ExperimentError(f"trials[{index}].condition must be baseline or skill")
        if require_text(trial.get("model_id"), f"trials[{index}].model_id") != model_id:
            raise ExperimentError(f"trials[{index}].model_id differs from scope.model_id")
        if require_text(trial.get("harness_id"), f"trials[{index}].harness_id") != harness_id:
            raise ExperimentError(f"trials[{index}].harness_id differs from scope.harness_id")
        stratum = require_text(trial.get("stratum"), f"trials[{index}].stratum")
        if stratum not in config.stratum_weights:
            raise ExperimentError(f"trials[{index}].stratum is absent from analysis.stratum_weights")
        if not require_bool(trial.get("trial_complete"), f"trials[{index}].trial_complete"):
            raise ExperimentError(f"trials[{index}] is incomplete and cannot be analyzed")
        _ = require_bool(trial.get("hidden_repair_pass"), f"trials[{index}].hidden_repair_pass")
        order = require_integer(trial.get("execution_order"), f"trials[{index}].execution_order", minimum=1)
        if order > 2:
            raise ExperimentError(f"trials[{index}].execution_order must be 1 or 2")
        _ = require_integer(trial.get("replicate_index"), f"trials[{index}].replicate_index", minimum=1)
        grouped[pair_id].append(trial)

    observations: list[PairObservation] = []
    observed_replicates: dict[str, set[int]] = defaultdict(set)
    for pair_id, pair in grouped.items():
        if len(pair) != 2:
            raise ExperimentError(f"pair {pair_id} must contain exactly one baseline and one skill trial")
        conditions = {require_text(trial["condition"], f"pair {pair_id} condition") for trial in pair}
        if conditions != {"baseline", "skill"}:
            raise ExperimentError(f"pair {pair_id} must contain exactly one baseline and one skill trial")
        if {require_integer(trial["execution_order"], f"pair {pair_id} execution order") for trial in pair} != {1, 2}:
            raise ExperimentError(f"pair {pair_id} must use both randomized execution orders")
        task_ids = {require_text(trial.get("task_id"), f"pair {pair_id} task_id") for trial in pair}
        strata = {require_text(trial.get("stratum"), f"pair {pair_id} stratum") for trial in pair}
        replicate_indices = {
            require_integer(trial.get("replicate_index"), f"pair {pair_id} replicate_index", minimum=1)
            for trial in pair
        }
        if len(task_ids) != 1 or len(strata) != 1 or len(replicate_indices) != 1:
            raise ExperimentError(f"pair {pair_id} must keep task_id, stratum, and replicate_index fixed across conditions")
        task_id = next(iter(task_ids))
        stratum = next(iter(strata))
        replicate_index = next(iter(replicate_indices))
        if task_plan.task_strata.get(task_id) != stratum:
            raise ExperimentError(f"pair {pair_id} is not in the preregistered task plan")
        if replicate_index > task_plan.pairs_per_task:
            raise ExperimentError(f"pair {pair_id} exceeds stopping_rule.pairs_per_task")
        if replicate_index in observed_replicates[task_id]:
            raise ExperimentError(f"task {task_id} has duplicate replicate_index {replicate_index}")
        observed_replicates[task_id].add(replicate_index)
        by_condition = {cast(Condition, trial["condition"]): trial for trial in pair}
        baseline = by_condition["baseline"]
        skill = by_condition["skill"]
        skill_first = require_integer(skill["execution_order"], f"pair {pair_id} skill execution order") == 1
        if skill_first != skill_first_for(config.random_seed, task_id, replicate_index):
            raise ExperimentError(f"pair {pair_id} does not match the preregistered randomized condition order")
        baseline_causal = baseline.get("blinded_causal_score")
        skill_causal = skill.get("blinded_causal_score")
        causal_difference: float | None = None
        if baseline_causal is not None or skill_causal is not None:
            if baseline_causal is None or skill_causal is None:
                raise ExperimentError(f"pair {pair_id} must either provide both blinded_causal_score values or neither")
            baseline_score = require_probability(
                baseline_causal,
                f"pair {pair_id} baseline blinded_causal_score",
                upper_inclusive=True,
            )
            skill_score = require_probability(
                skill_causal,
                f"pair {pair_id} skill blinded_causal_score",
                upper_inclusive=True,
            )
            causal_difference = skill_score - baseline_score
        observations.append(
            PairObservation(
                task_id=task_id,
                stratum=stratum,
                repair_difference=float(require_bool(skill["hidden_repair_pass"], f"pair {pair_id} skill repair")) - float(require_bool(baseline["hidden_repair_pass"], f"pair {pair_id} baseline repair")),
                causal_difference=causal_difference,
            )
        )
    if set(observed_replicates) != set(task_plan.task_strata):
        raise ExperimentError("completed trials must include every preregistered task exactly as planned")
    expected_replicates = set(range(1, task_plan.pairs_per_task + 1))
    for task_id, replicates in observed_replicates.items():
        if replicates != expected_replicates:
            raise ExperimentError(f"task {task_id} does not satisfy the fixed stopping rule")
    return observations


def analyze_metric(
    observations: Iterable[PairObservation],
    config: AnalysisConfig,
    *,
    metric: MetricName,
) -> MetricReport:
    task_values: dict[str, list[float]] = defaultdict(list)
    task_strata: dict[str, str] = {}
    paired_runs = 0
    for observation in observations:
        value = observation.repair_difference if metric == "hidden_repair_success" else observation.causal_difference
        if value is None:
            continue
        if observation.task_id in task_strata and task_strata[observation.task_id] != observation.stratum:
            raise ExperimentError(f"task {observation.task_id} appears in multiple strata")
        task_values[observation.task_id].append(value)
        task_strata[observation.task_id] = observation.stratum
        paired_runs += 1
    distinct_tasks = len(task_values)
    if distinct_tasks == 0:
        return {
            "metric": metric,
            "eligible": False,
            "decision": "not_measured",
            "distinct_tasks": 0,
            "paired_runs": 0,
            "effect": None,
            "confidence_interval_95": None,
            "one_sided_randomization_p_value": None,
            "randomization_method": None,
            "reason": "No paired observations supplied this metric.",
        }
    missing_strata = set(config.stratum_weights) - set(task_strata.values())
    if missing_strata:
        missing = ", ".join(sorted(missing_strata))
        raise ExperimentError(f"metric {metric} is missing preregistered strata: {missing}")
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
    enough_tasks = distinct_tasks >= config.minimum_distinct_tasks
    meets_threshold = interval[0] > config.minimum_effect and p_value < config.alpha
    if enough_tasks and meets_threshold:
        decision = "improved"
        reason = "The preregistered lower confidence bound exceeds the practical threshold and the paired randomization test passes."
    elif enough_tasks and interval[1] <= 0:
        decision = "no_demonstrated_improvement"
        reason = "The upper confidence bound is non-positive; the data do not support an improvement claim."
    else:
        decision = "inconclusive"
        reason = "The data do not meet every preregistered task-count, confidence-bound, and randomization threshold."
    return {
        "metric": metric,
        "eligible": enough_tasks,
        "decision": decision,
        "distinct_tasks": distinct_tasks,
        "paired_runs": paired_runs,
        "effect": effect,
        "confidence_interval_95": interval,
        "one_sided_randomization_p_value": p_value,
        "randomization_method": method,
        "reason": reason,
    }


def analyze_experiment(experiment: Mapping[str, object]) -> AnalysisReport:
    if require_integer(experiment.get("schema_version"), "schema_version") != 1:
        raise ExperimentError("schema_version must be 1")
    experiment_id = require_text(experiment.get("experiment_id"), "experiment_id")
    status = require_text(experiment.get("status"), "status")
    if status not in ("planned", "completed"):
        raise ExperimentError("status must be planned or completed")
    planned = status == "planned"
    scope = require_object(experiment.get("scope"), "scope")
    _ = require_text(scope.get("claim"), "scope.claim")
    _ = require_sha256(scope.get("skill_revision_sha256"), "scope.skill_revision_sha256", allow_pending=planned)
    config = parse_config(experiment, planned=planned)
    task_plan = parse_task_plan(experiment, config, planned=planned)
    if planned:
        if require_list(experiment.get("trials"), "trials"):
            raise ExperimentError("planned experiments must not contain trials")
        empty_repair = analyze_metric((), config, metric="hidden_repair_success")
        empty_causal = analyze_metric((), config, metric="blinded_causal_quality")
        return {
            "experiment_id": experiment_id,
            "status": status,
            "scope": scope,
            "primary_metric": empty_repair,
            "secondary_metric": empty_causal,
            "conclusion": "not_run: this preregistration is a protocol, not evidence that the Skill improves a model.",
            "limitations": ["No trial data have been recorded.", "A preregistration alone cannot establish a causal effect."],
        }
    observations = parse_pair_observations(experiment, config, task_plan)
    primary = analyze_metric(observations, config, metric="hidden_repair_success")
    secondary = analyze_metric(observations, config, metric="blinded_causal_quality")
    if primary["decision"] == "improved":
        conclusion = "improved within the preregistered model, harness, corpus, and hidden-scoring scope"
    else:
        conclusion = "no scoped repair-success improvement has been demonstrated"
    return {
        "experiment_id": experiment_id,
        "status": status,
        "scope": scope,
        "primary_metric": primary,
        "secondary_metric": secondary,
        "conclusion": conclusion,
        "limitations": [
            "The result cannot prove a model-wide, repository-wide, or production causal effect.",
            "A native subagent worktree is protocol isolation, not a container security boundary.",
            "The causal-quality metric is secondary and must be evaluated blind to condition.",
        ],
    }


def load_experiment(path: Path) -> dict[str, object]:
    try:
        value = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except json.JSONDecodeError as error:
        raise ExperimentError(f"{path} is not valid JSON: {error.msg}") from error
    return require_object(value, str(path))


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze a preregistered paired Skill-effect experiment.")
    _ = parser.add_argument("experiment", type=Path, help="JSON preregistration plus trial records")
    _ = parser.add_argument("--output", type=Path, help="Write the JSON report to this path instead of stdout")
    _ = parser.add_argument("--require-improvement", action="store_true", help="Exit nonzero unless the primary metric is improved")
    arguments = cast(CommandArguments, cast(object, parser.parse_args()))
    report = analyze_experiment(load_experiment(arguments.experiment))
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    output = arguments.output
    if output is None:
        print(rendered, end="")
    else:
        _ = output.write_text(rendered, encoding="utf-8")
    return 0 if not arguments.require_improvement or report["primary_metric"]["decision"] == "improved" else 1


if __name__ == "__main__":
    raise SystemExit(main())
