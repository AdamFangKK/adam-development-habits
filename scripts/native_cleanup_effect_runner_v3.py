#!/usr/bin/env python3
"""Execute native cleanup-effect conditions with an enforced predecessor-score chain."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from native_cleanup_effect_runner_v1 import copy_public_tree, manifest_task, score_trial


CONDITIONS = ("no_skill", "old_skill", "new_skill")
PREPARE_ARTIFACTS = {"sequence.json", "prepare.json", "seed.txt"}
FINAL_ARTIFACTS = PREPARE_ARTIFACTS | {"agent-result.json", "candidate.diff", "score.json"}


@dataclass(frozen=True)
class PreparedCondition:
    task_id: str
    condition: str
    seed_commit: str
    predecessor_score_sha256: tuple[dict[str, str], ...]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return cast(dict[str, object], value)


def run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)


def initialize_git(workspace: Path) -> str:
    for command in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "native-effect@example.invalid"],
        ["git", "config", "user.name", "Native Effect Trial"],
        ["git", "add", "."],
        ["git", "commit", "-qm", "seed"],
    ):
        result = run(command, cwd=workspace)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or f"seed command failed: {command!r}")
    result = run(["git", "rev-parse", "HEAD"], cwd=workspace)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "cannot read seed commit")
    return result.stdout.strip()


def plan_for(preregistration: Path, task_id: str) -> tuple[str, ...]:
    record = load_json(preregistration)
    plan = record.get("task_plan")
    if not isinstance(plan, dict) or not isinstance(plan.get("tasks"), list):
        raise ValueError("preregistration has no task plan")
    for item in cast(list[object], plan["tasks"]):
        if isinstance(item, dict) and item.get("task_id") == task_id:
            order = item.get("execution_order")
            if not isinstance(order, list) or tuple(order) not in _valid_orders():
                raise ValueError(f"task {task_id} has an invalid condition order")
            return tuple(cast(list[str], order))
    raise KeyError(f"task absent from preregistration: {task_id}")


def _valid_orders() -> set[tuple[str, ...]]:
    from itertools import permutations

    return set(permutations(CONDITIONS))


def existing_condition_directories(raw_task: Path) -> set[str]:
    if not raw_task.exists():
        return set()
    if not raw_task.is_dir():
        raise ValueError(f"raw task path is not a directory: {raw_task}")
    paths = {entry.name for entry in raw_task.iterdir() if entry.is_dir()}
    files = [entry.name for entry in raw_task.iterdir() if entry.is_file()]
    if files:
        raise ValueError(f"raw task path has unexpected files: {', '.join(sorted(files))}")
    if paths.difference(CONDITIONS):
        raise ValueError(f"raw task path has unknown condition directories: {', '.join(sorted(paths.difference(CONDITIONS)))}")
    return paths


def read_scored_predecessor(directory: Path, *, task_id: str, condition: str) -> dict[str, str]:
    if not directory.is_dir():
        raise ValueError(f"predecessor condition is missing: {condition}")
    names = {entry.name for entry in directory.iterdir()}
    if names != FINAL_ARTIFACTS:
        raise ValueError(f"predecessor {condition} has incomplete or unexpected artifacts")
    score_path = directory / "score.json"
    score = load_json(score_path)
    if score.get("task_id") != task_id:
        raise ValueError(f"predecessor {condition} score task ID mismatch")
    if score.get("hidden_injected_after_agent_exit") is not True:
        raise ValueError(f"predecessor {condition} was not post-exit scored")
    return {"condition": condition, "sha256": sha256(score_path)}


def write_json(path: Path, value: dict[str, object]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def prepare_condition(
    corpus: Path,
    preregistration: Path,
    source_root: Path,
    raw_root: Path,
    task_id: str,
    condition: str,
    workspace: Path,
) -> PreparedCondition:
    order = plan_for(preregistration, task_id)
    if condition not in order:
        raise ValueError(f"unknown condition: {condition}")
    position = order.index(condition)
    raw_task = raw_root / task_id
    existing = existing_condition_directories(raw_task)
    predecessors = order[:position]
    if existing != set(predecessors):
        raise ValueError(
            f"cannot prepare {task_id}/{condition}: expected only scored predecessors {list(predecessors)!r}, found {sorted(existing)!r}"
        )
    if workspace.exists():
        raise FileExistsError(f"trial workspace already exists: {workspace}")

    predecessor_hashes = tuple(
        read_scored_predecessor(raw_task / previous, task_id=task_id, condition=previous)
        for previous in predecessors
    )
    raw_condition = raw_task / condition
    raw_condition.mkdir(parents=True)
    task = manifest_task(corpus, task_id)
    source = corpus / str(task["workspace_path"])
    copy_public_tree(source, workspace)
    if condition in {"old_skill", "new_skill"}:
        snapshot = source_root / f"examples/effect-experiment-native-v3/skills/{'old' if condition == 'old_skill' else 'new'}/frozen-policy.md"
        if not snapshot.is_file():
            raise FileNotFoundError(f"frozen policy snapshot is missing: {snapshot}")
        _ = shutil.copy2(snapshot, workspace / "frozen-policy.md")
    seed = initialize_git(workspace)
    sequence = {
        "schema_version": 1,
        "task_id": task_id,
        "condition": condition,
        "condition_index": position + 1,
        "execution_order": list(order),
        "predecessor_score_sha256": list(predecessor_hashes),
    }
    write_json(raw_condition / "sequence.json", sequence)
    write_json(
        raw_condition / "prepare.json",
        {
            "task_id": task_id,
            "condition": condition,
            "allowed_edit_paths": task["allowed_edit_paths"],
            "seed_commit": seed,
            "predecessor_score_sha256": list(predecessor_hashes),
        },
    )
    (raw_condition / "seed.txt").write_text(seed + "\n", encoding="utf-8")
    return PreparedCondition(task_id, condition, seed, predecessor_hashes)


def mark_agent_complete(raw_root: Path, task_id: str, condition: str) -> None:
    directory = raw_root / task_id / condition
    if {entry.name for entry in directory.iterdir()} != PREPARE_ARTIFACTS:
        raise ValueError("agent completion requires exactly the prepared artifacts")
    write_json(directory / "agent-result.json", {"status": "agent_exited", "task_id": task_id, "condition": condition})


def score_condition(corpus: Path, raw_root: Path, task_id: str, condition: str, workspace: Path) -> dict[str, object]:
    directory = raw_root / task_id / condition
    required_before_score = PREPARE_ARTIFACTS | {"agent-result.json"}
    if {entry.name for entry in directory.iterdir()} != required_before_score:
        raise ValueError("scoring requires a completed prepared condition with no prior score artifacts")
    seed = (directory / "seed.txt").read_text(encoding="utf-8").strip()
    if len(seed) != 40:
        raise ValueError("seed.txt must contain a Git commit SHA")
    result = run(["git", "diff", "--binary", seed], cwd=workspace)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "cannot write candidate diff")
    (directory / "candidate.diff").write_text(result.stdout, encoding="utf-8")
    score = score_trial(corpus, task_id, workspace, seed)
    score["pre_score_artifact_sha256"] = {
        name: sha256(directory / name)
        for name in ("sequence.json", "prepare.json", "seed.txt", "agent-result.json", "candidate.diff")
    }
    write_json(directory / "score.json", score)
    return score


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--corpus", type=Path, required=True)
    prepare.add_argument("--preregistration", type=Path, required=True)
    prepare.add_argument("--source-root", type=Path, required=True)
    prepare.add_argument("--raw-root", type=Path, required=True)
    prepare.add_argument("--task", required=True)
    prepare.add_argument("--condition", required=True, choices=CONDITIONS)
    prepare.add_argument("--workspace", type=Path, required=True)
    complete = commands.add_parser("mark-agent-complete")
    complete.add_argument("--raw-root", type=Path, required=True)
    complete.add_argument("--task", required=True)
    complete.add_argument("--condition", required=True, choices=CONDITIONS)
    score = commands.add_parser("score")
    score.add_argument("--corpus", type=Path, required=True)
    score.add_argument("--raw-root", type=Path, required=True)
    score.add_argument("--task", required=True)
    score.add_argument("--condition", required=True, choices=CONDITIONS)
    score.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare_condition(args.corpus, args.preregistration, args.source_root, args.raw_root, args.task, args.condition, args.workspace)
        print(json.dumps({"task_id": result.task_id, "condition": result.condition, "seed_commit": result.seed_commit, "predecessor_score_sha256": result.predecessor_score_sha256}, sort_keys=True))
    elif args.command == "mark-agent-complete":
        mark_agent_complete(args.raw_root, args.task, args.condition)
    else:
        print(json.dumps(score_condition(args.corpus, args.raw_root, args.task, args.condition, args.workspace), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
