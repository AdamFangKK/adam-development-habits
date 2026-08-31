#!/usr/bin/env python3
"""Prepare and blind-score isolated workspaces for native cleanup-effect trials."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast


@dataclass(frozen=True)
class PreparedTrial:
    task_id: str
    seed_commit: str
    allowed_edit_paths: tuple[str, ...]


def run(command: list[str], *, cwd: Path, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False)


def no_symlinks(root: Path) -> None:
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"symbolic link not allowed: {path}")


def copy_public_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        raise FileExistsError(f"trial workspace already exists: {destination}")
    no_symlinks(source)
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))


def manifest_task(corpus: Path, task_id: str) -> dict[str, object]:
    value = cast(dict[str, Any], json.loads((corpus / "manifest.json").read_text(encoding="utf-8")))
    for item in cast(list[dict[str, object]], value["tasks"]):
        if item.get("task_id") == task_id:
            return item
    raise KeyError(f"unknown task: {task_id}")


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


def prepare_trial(corpus: Path, task_id: str, workspace: Path) -> PreparedTrial:
    """Copy only public input into an agent workspace and establish a Git baseline."""
    task = manifest_task(corpus, task_id)
    source = corpus / str(task["workspace_path"])
    copy_public_tree(source, workspace)
    return PreparedTrial(
        task_id=task_id,
        seed_commit=initialize_git(workspace),
        allowed_edit_paths=tuple(cast(list[str], task["allowed_edit_paths"])),
    )


def changed_paths(workspace: Path, seed_commit: str) -> list[str]:
    tracked = run(["git", "diff", "--name-only", "--diff-filter=ACDMRT", seed_commit], cwd=workspace)
    untracked = run(["git", "ls-files", "--others", "--exclude-standard"], cwd=workspace)
    if tracked.returncode != 0 or untracked.returncode != 0:
        raise RuntimeError("cannot determine candidate changes")
    return sorted({line.strip() for line in (tracked.stdout + "\n" + untracked.stdout).splitlines() if line.strip()})


def suite_result(workspace: Path) -> dict[str, object]:
    try:
        result = run(["python3", "-m", "unittest", "discover", "-s", "tests"], cwd=workspace)
        return {
            "passed": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timeout": False,
        }
    except subprocess.TimeoutExpired as error:
        return {
            "passed": False,
            "returncode": None,
            "stdout": str(error.stdout or ""),
            "stderr": str(error.stderr or ""),
            "timeout": True,
        }


def score_trial(corpus: Path, task_id: str, workspace: Path, seed_commit: str) -> dict[str, object]:
    """Score a candidate without a condition label and after the agent has exited."""
    task = manifest_task(corpus, task_id)
    no_symlinks(workspace)
    paths = changed_paths(workspace, seed_commit)
    allowed = set(cast(list[str], task["allowed_edit_paths"]))
    disallowed = sorted(set(paths) - allowed)
    public = suite_result(workspace)
    result: dict[str, object] = {
        "task_id": task_id,
        "changed_paths": paths,
        "disallowed_changed_paths": disallowed,
        "implementation_integrity_passed": not disallowed,
        "public_result": public,
        "hidden_injected_after_agent_exit": False,
        "hidden_repair_passed": False,
    }
    if disallowed:
        return result

    hidden_source = corpus / str(task["hidden_tests_path"])
    with tempfile.TemporaryDirectory(prefix="native-cleanup-score-") as directory:
        candidate = Path(directory) / "candidate"
        copy_public_tree(workspace, candidate)
        shutil.rmtree(candidate / ".git", ignore_errors=True)
        hidden_target = candidate / "tests" / "test_hidden.py"
        hidden_target.parent.mkdir(parents=True, exist_ok=True)
        _ = shutil.copy2(hidden_source / "tests" / "test_hidden.py", hidden_target)
        hidden = suite_result(candidate)
    result["hidden_injected_after_agent_exit"] = True
    result["hidden_result"] = hidden
    result["hidden_repair_passed"] = bool(hidden["passed"])
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--corpus", type=Path, required=True)
    prepare.add_argument("--task", required=True)
    prepare.add_argument("--workspace", type=Path, required=True)
    score = subparsers.add_parser("score")
    score.add_argument("--corpus", type=Path, required=True)
    score.add_argument("--task", required=True)
    score.add_argument("--workspace", type=Path, required=True)
    score.add_argument("--seed-commit", required=True)
    arguments = parser.parse_args()
    if arguments.command == "prepare":
        prepared = prepare_trial(arguments.corpus, arguments.task, arguments.workspace)
        print(json.dumps({"task_id": prepared.task_id, "seed_commit": prepared.seed_commit, "allowed_edit_paths": prepared.allowed_edit_paths}, sort_keys=True))
        return 0
    print(json.dumps(score_trial(arguments.corpus, arguments.task, arguments.workspace, arguments.seed_commit), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
