#!/usr/bin/env python3
"""Audit captured V8 condition artifacts before any effect analysis."""

# pyright: reportMissingTypeStubs=false

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import cast


SNAPSHOT_PROMPT = re.compile(r"The supplied Skill path is: (?P<path>[^\s]+/SKILL\.md)")
ISOLATION_MARKER = "V8 isolation wrapper: --disable skill_search"


def load_object(path: Path) -> dict[str, object]:
    value = cast(object, json.loads(path.read_text(encoding="utf-8")))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return cast(dict[str, object], value)


def audit_collection(raw_root: Path, result_path: Path, source_skill: Path) -> dict[str, object]:
    """Return a machine-readable pass/fail report for the V8 isolation contract."""
    result = load_object(result_path)
    trials = result.get("trials")
    failures: list[str] = []
    if not isinstance(trials, list) or not trials:
        return {"passed": False, "failures": ["result.trials is empty or not a list"]}

    forbidden_paths = {str(source_skill), str(source_skill.resolve())}
    trial_values = cast(list[object], trials)
    for trial_value in trial_values:
        if not isinstance(trial_value, dict):
            failures.append("trial record is not an object")
            continue
        trial = cast(dict[str, object], trial_value)
        condition = str(trial.get("condition", ""))
        artifact_path = trial.get("artifact_path")
        if not isinstance(artifact_path, str) or not artifact_path:
            failures.append("trial has no artifact_path")
            continue
        artifact = raw_root / artifact_path
        stderr_path = artifact / "agent.stderr.log"
        output_path = artifact / "agent-output.md"
        if not stderr_path.is_file():
            failures.append(f"{artifact_path}: missing agent.stderr.log")
            continue
        if not output_path.is_file() or not output_path.read_text(encoding="utf-8").strip():
            failures.append(f"{artifact_path}: missing or empty absolute agent-output.md")
        stderr = stderr_path.read_text(encoding="utf-8")
        if ISOLATION_MARKER not in stderr:
            failures.append(f"{artifact_path}: missing --disable skill_search wrapper evidence")
        if any(path in stderr for path in forbidden_paths) or "/.codex/skills/adam-development-habits/SKILL.md" in stderr:
            failures.append(f"{artifact_path}: condition read a globally available Adam Skill")
        if condition == "skill":
            match = SNAPSHOT_PROMPT.search(stderr)
            if match is None:
                failures.append(f"{artifact_path}: treatment did not receive a supplied Skill path")
            else:
                snapshot = match.group("path")
                read_command = re.compile(r"exec\s*\n[^\n]*" + re.escape(snapshot))
                if read_command.search(stderr) is None:
                    failures.append(f"{artifact_path}: treatment did not read the supplied Skill snapshot")
        elif condition != "baseline":
            failures.append(f"{artifact_path}: unknown condition {condition!r}")

    return {"passed": not failures, "failures": failures, "trial_count": len(trial_values)}


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("--raw-root", type=Path, required=True)
    _ = parser.add_argument("--result", type=Path, required=True)
    _ = parser.add_argument("--skill", type=Path, required=True)
    arguments = cast(dict[str, object], vars(parser.parse_args()))
    report = audit_collection(
        cast(Path, arguments["raw_root"]),
        cast(Path, arguments["result"]),
        cast(Path, arguments["skill"]),
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
