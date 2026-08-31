#!/usr/bin/env python3
"""Audit V9 raw artifacts and prove condition-level protocol isolation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
from pathlib import Path
from typing import cast


CONDITIONS = ("no_skill", "old_skill", "new_skill")
WRAPPER_MARKER = "V9 isolation wrapper: --disable skill_search"
REQUIRED_ARTIFACTS = (
    "agent.stdout.log",
    "agent.stderr.log",
    "agent-output.md",
    "candidate.diff",
    "public.json",
    "hidden-score.json",
)


def load_object(path: Path) -> dict[str, object]:
    value = cast(object, json.loads(path.read_text(encoding="utf-8")))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return cast(dict[str, object], value)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command_log(text: str) -> list[dict[str, object]]:
    """Extract only completed Codex command events, never prose assertions."""
    commands: list[dict[str, object]] = []

    def visit(value: object) -> None:
        if isinstance(value, dict):
            item = cast(dict[str, object], value)
            if (
                item.get("type") == "command_execution"
                and item.get("status") == "completed"
                and isinstance(item.get("command"), str)
            ):
                commands.append(item)
            for child in item.values():
                visit(child)
        elif isinstance(value, list):
            for child in cast(list[object], value):
                visit(child)

    for line in text.splitlines():
        try:
            visit(cast(object, json.loads(line)))
        except json.JSONDecodeError:
            continue
    return commands


def exact_cat_target(command: str) -> str | None:
    try:
        parts = shlex.split(command)
        if len(parts) == 3 and Path(parts[0]).name in {"sh", "bash", "zsh"} and parts[1] in {"-c", "-lc"}:
            parts = shlex.split(parts[2])
    except ValueError:
        return None
    if len(parts) != 2 or Path(parts[0]).name != "cat":
        return None
    return parts[1]


def proves_skill_read(commands: list[dict[str, object]], skill: Path) -> bool:
    expected_output = skill.read_text(encoding="utf-8")
    expected_path = str(skill.resolve())
    return any(
        isinstance(event.get("command"), str)
        and exact_cat_target(cast(str, event["command"])) == expected_path
        and event.get("exit_code") == 0
        and event.get("aggregated_output") == expected_output
        for event in commands
    )


def audit_collection(
    raw_root: Path,
    result_path: Path,
    *,
    old_skill: Path,
    new_skill: Path,
    corpus: Path | None = None,
) -> dict[str, object]:
    result = load_object(result_path)
    raw_trials = result.get("trials")
    failures: list[str] = []
    if not isinstance(raw_trials, list) or not raw_trials:
        return {"passed": False, "failures": ["result.trials is empty or not a list"], "trial_count": 0}

    expected_snapshots = {
        "old_skill": str(old_skill.resolve()),
        "new_skill": str(new_skill.resolve()),
    }
    expected_digests = {
        "old_skill": digest(old_skill),
        "new_skill": digest(new_skill),
    }
    task_plan = result.get("task_plan")
    planned_values = task_plan.get("tasks") if isinstance(task_plan, dict) else None
    planned_tasks = {
        value.get("task_id")
        for value in cast(list[object], planned_values)
        if isinstance(value, dict) and isinstance(value.get("task_id"), str)
    } if isinstance(planned_values, list) else set()
    if not planned_tasks:
        failures.append("result.task_plan.tasks is empty or invalid")
    seen: set[tuple[str, str]] = set()
    for index, value in enumerate(cast(list[object], raw_trials)):
        if not isinstance(value, dict):
            failures.append(f"trials[{index}] is not an object")
            continue
        trial = cast(dict[str, object], value)
        condition = trial.get("condition")
        task_id = trial.get("task_id")
        if condition not in CONDITIONS:
            failures.append(f"trials[{index}] has unknown condition")
            continue
        if not isinstance(task_id, str) or not task_id:
            failures.append(f"trials[{index}] has no task_id")
            continue
        artifact_path = trial.get("artifact_path")
        if not isinstance(artifact_path, str) or not artifact_path or Path(artifact_path).is_absolute() or ".." in Path(artifact_path).parts:
            failures.append(f"{task_id}/{condition}: artifact_path must be relative")
            continue
        key = (task_id, cast(str, condition))
        if key in seen:
            failures.append(f"{task_id}/{condition}: duplicate trial")
        seen.add(key)
        artifact = raw_root / artifact_path
        if not artifact.is_dir() or artifact.is_symlink():
            failures.append(f"{task_id}/{condition}: artifact directory missing or unsafe")
            continue
        for filename in REQUIRED_ARTIFACTS:
            path = artifact / filename
            if not path.is_file() or path.is_symlink():
                failures.append(f"{task_id}/{condition}: missing artifact {filename}")
        stdout = (artifact / "agent.stdout.log").read_text(encoding="utf-8") if (artifact / "agent.stdout.log").is_file() else ""
        stderr = (artifact / "agent.stderr.log").read_text(encoding="utf-8") if (artifact / "agent.stderr.log").is_file() else ""
        commands = command_log(stdout)
        output = (artifact / "agent-output.md").read_text(encoding="utf-8") if (artifact / "agent-output.md").is_file() else ""
        if not output.strip():
            failures.append(f"{task_id}/{condition}: agent-output.md is empty")
        if trial.get("agent_output_present") is not True:
            failures.append(f"{task_id}/{condition}: result records no absolute Agent output")
        if WRAPPER_MARKER not in stderr:
            failures.append(f"{task_id}/{condition}: missing skill-search isolation marker")
        global_skill = "/.codex/skills/adam-development-habits/SKILL.md"
        command_text = "\n".join(
            cast(str, event["command"])
            for event in commands
            if isinstance(event.get("command"), str)
        )
        if corpus is not None and any(
            str((corpus / forbidden).resolve()) in command_text
            for forbidden in ("hidden-tests", "references")
        ):
            failures.append(f"{task_id}/{condition}: Agent command accessed a scorer-only corpus path")
        if global_skill in command_text or str(old_skill.resolve()) in command_text and condition != "old_skill" or str(new_skill.resolve()) in command_text and condition != "new_skill":
            failures.append(f"{task_id}/{condition}: agent log contains an unexpected Skill source")
        if condition == "no_skill" and "SKILL.md" in command_text:
            failures.append(f"{task_id}/{condition}: no_skill condition received a Skill path")
        if condition in expected_snapshots:
            snapshot = expected_snapshots[cast(str, condition)]
            if not proves_skill_read(commands, Path(snapshot)):
                failures.append(f"{task_id}/{condition}: Agent did not complete a full read of the frozen Skill snapshot")
            if trial.get("skill_snapshot_integrity_passed") is not True:
                failures.append(f"{task_id}/{condition}: Skill snapshot integrity flag is not true")
            if trial.get("skill_snapshot_sha256") != expected_digests[cast(str, condition)]:
                failures.append(f"{task_id}/{condition}: Skill snapshot digest differs from the frozen input")
        hidden_path = artifact / "hidden-score.json"
        if hidden_path.is_file():
            try:
                hidden = load_object(hidden_path)
            except (OSError, json.JSONDecodeError, ValueError) as error:
                failures.append(f"{task_id}/{condition}: hidden-score.json invalid: {error}")
            else:
                if hidden.get("implementation_integrity_passed") is not True:
                    failures.append(f"{task_id}/{condition}: implementation integrity failed")
                if hidden.get("passed") is not bool(trial.get("hidden_scorer_pass")):
                    failures.append(f"{task_id}/{condition}: result does not match hidden scorer")
        public_path = artifact / "public.json"
        if public_path.is_file():
            try:
                public = load_object(public_path)
            except (OSError, json.JSONDecodeError, ValueError) as error:
                failures.append(f"{task_id}/{condition}: public.json invalid: {error}")
            else:
                if bool(public.get("passed")) is not bool(trial.get("public_pass")):
                    failures.append(f"{task_id}/{condition}: result does not match public check")
        if trial.get("implementation_integrity_passed") is not True:
            failures.append(f"{task_id}/{condition}: trial integrity flag is not true")
    expected_pairs = {(task_id, condition) for task_id in planned_tasks for condition in CONDITIONS}
    if seen != expected_pairs:
        failures.append("result trials do not contain every planned task-condition exactly once")
    return {
        "passed": not failures,
        "failures": failures,
        "trial_count": len(cast(list[object], raw_trials)),
        "unique_task_condition_count": len(seen),
        "required_artifacts": list(REQUIRED_ARTIFACTS),
        "old_skill_sha256": digest(old_skill),
        "new_skill_sha256": digest(new_skill),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("--raw-root", type=Path, required=True)
    _ = parser.add_argument("--result", type=Path, required=True)
    _ = parser.add_argument("--old-skill", type=Path, required=True)
    _ = parser.add_argument("--new-skill", type=Path, required=True)
    _ = parser.add_argument("--corpus", type=Path, required=True)
    arguments = parser.parse_args()
    report = audit_collection(
        arguments.raw_root,
        arguments.result,
        old_skill=arguments.old_skill,
        new_skill=arguments.new_skill,
        corpus=arguments.corpus,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
