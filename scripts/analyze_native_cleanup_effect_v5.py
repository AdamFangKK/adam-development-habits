#!/usr/bin/env python3
"""Analyze one complete, preregistered V5 native cleanup-effect collection."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
import re
from typing import Any, Mapping, cast

from create_native_cleanup_effect_preregistration_v5 import ROOT, canonical_sha256, immutable_envelope
from materialize_native_cleanup_effect_v5 import materialize_native_cleanup_effect_v5
from native_cleanup_effect_runner_v1 import copy_public_tree, manifest_task, score_trial


CONDITIONS = ("no_skill", "old_skill", "new_skill")
REQUIRED_ARTIFACTS = ("sequence.json", "prepare.json", "seed.txt", "agent-prompt.txt", "agent-transcript.md", "agent-result.json", "candidate.diff", "score.json")


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


def required_utc_timestamp(value: object, field: str) -> str:
    text = required_text(value, field)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{field} must be an RFC 3339 timestamp") from error
    offset = parsed.utcoffset()
    if parsed.tzinfo is None or offset is None or offset.total_seconds() != 0:
        raise ValueError(f"{field} must be UTC")
    return text


def validate_preregistration(preregistration: dict[str, object], *, root: Path) -> list[dict[str, object]]:
    if preregistration.get("schema_version") != 2 or preregistration.get("status") != "planned":
        raise ValueError("V5 preregistration must be a planned schema_version 2 record")
    if preregistration.get("trials") != []:
        raise ValueError("V5 preregistration must not contain trial outcomes")
    protocol = preregistration.get("protocol")
    task_plan = preregistration.get("task_plan")
    metadata = preregistration.get("preregistration")
    if not isinstance(protocol, dict) or not isinstance(task_plan, dict) or not isinstance(metadata, dict):
        raise ValueError("V5 preregistration is missing protocol, task_plan, or metadata")
    if protocol.get("conditions") != list(CONDITIONS):
        raise ValueError("V5 preregistration conditions differ from the analyzer conditions")
    for name in ("corpus_manifest", "generator", "runner", "base_runner", "analyzer", "preregistration_generator", "task_prompt", "old_skill", "new_skill"):
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


def initialize_replay_git(workspace: Path) -> str:
    for command in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "native-effect-replay@example.invalid"],
        ["git", "config", "user.name", "Native Effect Replay"],
        ["git", "add", "."],
        ["git", "commit", "-qm", "replay-seed"],
    ):
        result = subprocess.run(command, cwd=workspace, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or f"replay seed command failed: {command!r}")
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=workspace, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "cannot read replay seed commit")
    return result.stdout.strip()


def expected_scorer_provenance(corpus: Path, task_id: str) -> dict[str, object]:
    task = manifest_task(corpus, task_id)
    return {
        "base_runner_path": "scripts/native_cleanup_effect_runner_v1.py",
        "base_runner_sha256": file_sha256(ROOT / "scripts/native_cleanup_effect_runner_v1.py"),
        "corpus_manifest_sha256": file_sha256(corpus / "manifest.json"),
        "hidden_tests_path": task["hidden_tests_path"],
        "hidden_tests_tree_sha256": task["hidden_tests_tree_sha256"],
        "reference_tree_sha256": task["reference_tree_sha256"],
        "workspace_tree_sha256": task["workspace_tree_sha256"],
    }


def replay_score(corpus: Path, *, task_id: str, condition: str, candidate_diff: Path, root: Path) -> dict[str, object]:
    """Rebuild public input, apply the recorded diff, and rerun the blind scorer."""
    task = manifest_task(corpus, task_id)
    source = corpus / required_text(task.get("workspace_path"), "task.workspace_path")
    with tempfile.TemporaryDirectory(prefix="native-cleanup-v5-replay-") as directory:
        workspace = Path(directory) / "candidate"
        copy_public_tree(source, workspace)
        if condition in {"old_skill", "new_skill"}:
            snapshot = root / f"examples/effect-experiment-native-v5/skills/{'old' if condition == 'old_skill' else 'new'}/SKILL.md"
            if not snapshot.is_file():
                raise FileNotFoundError(f"frozen policy snapshot is missing: {snapshot}")
            _ = shutil.copy2(snapshot, workspace / "frozen-policy.md")
        seed = initialize_replay_git(workspace)
        # An empty diff is a valid observed failed attempt: replay the pristine
        # public workspace rather than asking Git to apply a nonexistent patch.
        if candidate_diff.read_bytes():
            applied = subprocess.run(
                ["git", "apply", "--binary", str(candidate_diff.resolve())],
                cwd=workspace,
                capture_output=True,
                text=True,
                check=False,
            )
            if applied.returncode != 0:
                raise ValueError(f"candidate diff cannot be replayed: {applied.stderr.strip()}")
        return score_trial(corpus, task_id, workspace, seed)


def require_replay_match(score: dict[str, object], replayed: dict[str, object]) -> None:
    for field in ("task_id", "changed_paths", "disallowed_changed_paths", "implementation_integrity_passed", "hidden_injected_after_agent_exit", "hidden_repair_passed"):
        if score.get(field) != replayed.get(field):
            raise ValueError(f"score.{field} does not match the independent replay")
    for field in ("public_result", "hidden_result"):
        stored = score.get(field)
        actual = replayed.get(field)
        if not isinstance(stored, dict) or not isinstance(actual, dict):
            raise ValueError(f"score.{field} must be a scorer result object")
        if canonical_suite_result(stored) != canonical_suite_result(actual):
            raise ValueError(f"score.{field} does not match the independent replay's canonical result")


def canonical_suite_result(result: Mapping[str, object]) -> dict[str, object]:
    """Preserve result semantics while removing volatile runner directory names."""
    normalized: dict[str, object] = {}
    for field in ("passed", "returncode", "timeout"):
        normalized[field] = result.get(field)
    for field in ("stdout", "stderr"):
        value = result.get(field)
        if not isinstance(value, str):
            raise ValueError(f"suite result {field} must be text")
        normalized_value = re.sub(r"(Ran \d+ tests? in )\d+(?:\.\d+)?s", r"\1<duration>", value)
        normalized[field] = re.sub(
            r"(?:(?:/private)?/var/folders/[^/\s]+/[^/\s]+/T|/tmp)/native-cleanup-(?:score|v5-replay)-[^/\s]+/candidate",
            "<scoring-workspace>",
            normalized_value,
        )
    return normalized


def expected_agent_prompt(root: Path, condition: str) -> str:
    template = (root / "examples/effect-experiment-native-v5/agent-task-template.txt").read_text(encoding="utf-8")
    instruction = (
        "No frozen Skill snapshot is supplied for this condition."
        if condition == "no_skill"
        else "Read `frozen-policy.md` before editing and apply only that supplied frozen policy."
    )
    if "{policy_instruction}" not in template:
        raise ValueError("native V5 agent template lacks its policy placeholder")
    return template.replace("{policy_instruction}", instruction)


def expected_handoff_sha256(corpus: Path, *, task_id: str, condition: str, root: Path) -> str:
    task = manifest_task(corpus, task_id)
    source = corpus / required_text(task.get("workspace_path"), "task.workspace_path")
    with tempfile.TemporaryDirectory(prefix="native-cleanup-v5-handoff-") as directory:
        workspace = Path(directory) / "workspace"
        copy_public_tree(source, workspace)
        if condition != "no_skill":
            snapshot = root / f"examples/effect-experiment-native-v5/skills/{'old' if condition == 'old_skill' else 'new'}/SKILL.md"
            _ = shutil.copy2(snapshot, workspace / "frozen-policy.md")
        digest = hashlib.sha256()
        for path in sorted(workspace.rglob("*")):
            if not path.is_file() or ".git" in path.parts:
                continue
            relative = path.relative_to(workspace).as_posix().encode("utf-8")
            content = path.read_bytes()
            digest.update(len(relative).to_bytes(8, "big"))
            digest.update(relative)
            digest.update(len(content).to_bytes(8, "big"))
            digest.update(content)
        return digest.hexdigest()


def validate_agent_provenance(
    directory: Path,
    agent: dict[str, object],
    *,
    task_id: str,
    condition: str,
    prepare: dict[str, object],
    preregistration: dict[str, object],
    corpus: Path,
    root: Path,
) -> None:
    if agent.get("status") != "agent_exited" or agent.get("task_id") != task_id or agent.get("condition") != condition:
        raise ValueError(f"trial {task_id}/{condition} agent exit record is invalid")
    executor = agent.get("executor")
    if not isinstance(executor, dict) or executor.get("kind") != "codex-native-subagent":
        raise ValueError(f"trial {task_id}/{condition} lacks native-agent provenance")
    agent_id = required_text(executor.get("agent_id"), f"trial {task_id}/{condition}.executor.agent_id")
    if not agent_id.startswith("/root/"):
        raise ValueError(f"trial {task_id}/{condition} has an invalid native agent identity")
    scope = cast(dict[str, object], preregistration["scope"])
    if executor.get("model_id") != scope.get("model_id"):
        raise ValueError(f"trial {task_id}/{condition} model identity does not match preregistration")
    started = required_utc_timestamp(executor.get("started_at"), f"trial {task_id}/{condition}.executor.started_at")
    finished = required_utc_timestamp(executor.get("finished_at"), f"trial {task_id}/{condition}.executor.finished_at")
    if started > finished:
        raise ValueError(f"trial {task_id}/{condition} native-agent timestamps are not ordered")
    prompt_path = directory / "agent-prompt.txt"
    transcript_path = directory / "agent-transcript.md"
    if prompt_path.read_text(encoding="utf-8") != expected_agent_prompt(root, condition):
        raise ValueError(f"trial {task_id}/{condition} agent prompt differs from frozen input")
    expected_prompt_hash = file_sha256(prompt_path)
    if executor.get("agent_prompt_sha256") != expected_prompt_hash:
        raise ValueError(f"trial {task_id}/{condition} agent prompt hash is invalid")
    if executor.get("transcript_sha256") != file_sha256(transcript_path) or not transcript_path.read_text(encoding="utf-8").strip():
        raise ValueError(f"trial {task_id}/{condition} agent transcript provenance is invalid")
    if executor.get("condition_input_sha256") != prepare.get("condition_input_sha256"):
        raise ValueError(f"trial {task_id}/{condition} condition input fingerprint is invalid")
    expected_handoff = expected_handoff_sha256(corpus, task_id=task_id, condition=condition, root=root)
    if prepare.get("workspace_handoff_sha256") != expected_handoff or executor.get("workspace_handoff_sha256") != expected_handoff:
        raise ValueError(f"trial {task_id}/{condition} workspace handoff fingerprint is invalid")


def load_trial(corpus: Path, raw_root: Path, preregistration: dict[str, object], *, task_id: str, condition: str, order: list[str], root: Path) -> dict[str, object]:
    directory = raw_root / task_id / condition
    missing = [name for name in REQUIRED_ARTIFACTS if not (directory / name).is_file()]
    if missing:
        raise ValueError(f"trial {task_id}/{condition} is missing required artifacts: {', '.join(missing)}")
    unexpected = sorted(path.name for path in directory.iterdir() if path.name not in REQUIRED_ARTIFACTS)
    if unexpected:
        raise ValueError(f"trial {task_id}/{condition} has unexpected artifacts: {', '.join(unexpected)}")
    sequence = load_object(directory / "sequence.json")
    position = order.index(condition)
    expected_predecessors = [
        {"condition": previous, "sha256": file_sha256(raw_root / task_id / previous / "score.json")}
        for previous in order[:position]
    ]
    if sequence != {
        "schema_version": 1,
        "task_id": task_id,
        "condition": condition,
        "condition_index": position + 1,
        "execution_order": order,
        "predecessor_score_sha256": expected_predecessors,
    }:
        raise ValueError(f"trial {task_id}/{condition} has an invalid predecessor-score sequence credential")
    prepare = load_object(directory / "prepare.json")
    if (
        prepare.get("task_id") != task_id
        or prepare.get("condition") != condition
        or prepare.get("seed_commit") != (directory / "seed.txt").read_text(encoding="utf-8").strip()
        or prepare.get("predecessor_score_sha256") != expected_predecessors
    ):
        raise ValueError(f"trial {task_id}/{condition} preparation metadata does not match its sequence credential")
    agent = load_object(directory / "agent-result.json")
    validate_agent_provenance(directory, agent, task_id=task_id, condition=condition, prepare=prepare, preregistration=preregistration, corpus=corpus, root=root)
    score = load_object(directory / "score.json")
    expected_pre_score_artifacts = {
        name: file_sha256(directory / name)
        for name in ("sequence.json", "prepare.json", "seed.txt", "agent-prompt.txt", "agent-transcript.md", "agent-result.json", "candidate.diff")
    }
    if score.get("pre_score_artifact_sha256") != expected_pre_score_artifacts:
        raise ValueError(f"trial {task_id}/{condition} pre-score artifact binding is invalid")
    if score.get("task_id") != task_id:
        raise ValueError(f"trial {task_id}/{condition} score task ID mismatch")
    if score.get("scored_after_agent_exit") is not True:
        raise ValueError(f"trial {task_id}/{condition} score lacks an after-exit scoring credential")
    provenance = score.get("scorer_provenance")
    if provenance != expected_scorer_provenance(corpus, task_id):
        raise ValueError(f"trial {task_id}/{condition} scorer provenance does not match the frozen corpus")
    replayed = replay_score(corpus, task_id=task_id, condition=condition, candidate_diff=directory / "candidate.diff", root=root)
    require_replay_match(score, replayed)
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
    planned_task_ids = {cast(str, task["task_id"]) for task in tasks}
    raw_entries = list(raw_root.iterdir())
    observed_task_directories = {entry.name for entry in raw_entries if entry.is_dir()}
    unexpected_tasks = sorted(observed_task_directories - planned_task_ids)
    if unexpected_tasks:
        errors.append("raw collection has unexpected task directories: " + ", ".join(unexpected_tasks))
    unexpected_raw_files = sorted(entry.name for entry in raw_root.iterdir() if entry.is_file())
    if unexpected_raw_files:
        errors.append("raw collection has unexpected root files: " + ", ".join(unexpected_raw_files))
    for task in tasks:
        task_id = cast(str, task["task_id"])
        task_root = raw_root / task_id
        if not task_root.is_dir():
            continue
        task_files = sorted(entry.name for entry in task_root.iterdir() if entry.is_file())
        if task_files:
            errors.append(f"raw collection has unexpected task files for {task_id}: " + ", ".join(task_files))
        extra_conditions = sorted(
            entry.name for entry in task_root.iterdir() if entry.is_dir() and (task_id, entry.name) not in expected_directories
        )
        if extra_conditions:
            errors.append(f"raw collection has unexpected trial directories for {task_id}: " + ", ".join(extra_conditions))
    with tempfile.TemporaryDirectory(prefix="native-cleanup-v5-corpus-") as directory:
        corpus = Path(directory) / "corpus"
        generated_manifest = materialize_native_cleanup_effect_v5(corpus)
        committed_manifest = load_object(root / "examples/effect-experiment-native-v5/manifest.json")
        protocol = cast(dict[str, object], preregistration["protocol"])
        if generated_manifest != committed_manifest or file_sha256(corpus / "manifest.json") != protocol.get("corpus_manifest_sha256"):
            errors.append("replayed V5 corpus does not match the preregistered manifest")
        for task in tasks:
            task_id = cast(str, task["task_id"])
            order = cast(list[str], task["execution_order"])
            for condition in order:
                try:
                    trial = load_trial(corpus, raw_root, preregistration, task_id=task_id, condition=condition, order=order, root=root)
                    trial["cohort"] = task["cohort"]
                    trial["stratum"] = task["stratum"]
                    trial["execution_order"] = order.index(condition) + 1
                    trials.append(trial)
                    if not bool(trial["complete"]):
                        errors.append(f"trial {task_id}/{condition} failed a preregistered completion gate")
                except (RuntimeError, ValueError) as error:
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
    minimum_effect = analysis.get("minimum_effect")
    alpha = analysis.get("alpha")
    if not isinstance(minimum_effect, (int, float)) or isinstance(minimum_effect, bool):
        raise ValueError("analysis.minimum_effect must be numeric")
    if not isinstance(alpha, (int, float)) or isinstance(alpha, bool):
        raise ValueError("analysis.alpha must be numeric")
    demonstrated = bool(
        complete
        and primary_effect is not None
        and secondary_effect is not None
        and primary_p is not None
        and primary_effect >= minimum_effect
        and primary_p <= alpha
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
            "demonstrated_improvement: within the fixed model, Harness, V5 corpus, frozen Skill snapshots, and scorer."
            if demonstrated
            else "no_demonstrated_improvement: this collection does not satisfy the preregistered V5 claim rule."
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
