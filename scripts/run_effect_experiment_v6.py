#!/usr/bin/env python3
"""Run a checkpointed paired multi-file Codex repair experiment."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import signal
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from analyze_skill_effect import skill_first_for


DEFAULT_MODEL_ID = "gpt-5.6-terra"
DEFAULT_HARNESS_ID = "codex-cli-0.146.0-alpha.9.2;exec;workspace-write;ephemeral;checkpointed-v6"
@dataclass(frozen=True)
class TaskRecord:
    task_id: str
    stratum: str
    workspace_path: str
    hidden_root_path: str
    allowed_edit_paths: tuple[str, ...]
    public_command: tuple[str, ...]
    hidden_command: tuple[str, ...]


@dataclass(frozen=True)
class Arguments:
    corpus: Path
    prompts: Path
    skill: Path
    preregistration: Path
    preregistration_commit: str
    raw_output: Path
    output: Path
    seed: int
    codex: str
    model: str
    harness: str
    agent_timeout: float
    test_timeout: float


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value


def environment() -> dict[str, str]:
    return {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"}


def run_checked(command: list[str], *, cwd: Path, timeout: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, env=environment(), capture_output=True, text=True, timeout=timeout, check=False)


def run_agent(command: list[str], *, cwd: Path, timeout: float) -> tuple[int | None, str, str]:
    """Run one agent in a process group so a timeout cannot leak descendants."""
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=environment(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        return process.returncode, text_output(stdout), text_output(stderr)
    except subprocess.TimeoutExpired as error:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (AttributeError, OSError, ProcessLookupError):
            pass
        stdout, stderr = process.communicate()
        return None, text_output(stdout or error.stdout), text_output(stderr or error.stderr) + f"\nagent timeout after {timeout:.1f}s"


def command_value(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a non-empty list of non-empty strings")
    parts = cast(list[object], value)
    if not parts or any(not isinstance(part, str) or not part for part in parts):
        raise ValueError(f"{field} must be a non-empty list of non-empty strings")
    typed_parts = [part for part in parts if isinstance(part, str)]
    return tuple(typed_parts)


def path_values(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a non-empty list of relative paths")
    parts = cast(list[object], value)
    if not parts or any(not isinstance(part, str) or not part or Path(part).is_absolute() for part in parts):
        raise ValueError(f"{field} must be a non-empty list of relative paths")
    typed_parts = [part for part in parts if isinstance(part, str)]
    return tuple(typed_parts)


def task_from_value(value: object) -> TaskRecord:
    if not isinstance(value, dict):
        raise ValueError("manifest task must be an object")
    task_value = cast(dict[str, object], value)
    fields = ("task_id", "stratum", "workspace_path", "hidden_root_path")
    if any(not isinstance(task_value.get(field), str) or not str(task_value[field]).strip() for field in fields):
        raise ValueError("manifest task has missing text fields")
    return TaskRecord(
        task_id=cast(str, task_value["task_id"]),
        stratum=cast(str, task_value["stratum"]),
        workspace_path=cast(str, task_value["workspace_path"]),
        hidden_root_path=cast(str, task_value["hidden_root_path"]),
        allowed_edit_paths=path_values(task_value.get("allowed_edit_paths"), "allowed_edit_paths"),
        public_command=command_value(task_value.get("public_command"), "public_command"),
        hidden_command=command_value(task_value.get("hidden_command"), "hidden_command"),
    )


def load_json(path: Path) -> dict[str, object]:
    value = cast(object, json.loads(path.read_text(encoding="utf-8")))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return cast(dict[str, object], value)


def copy_tree(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    if any(destination.iterdir()):
        raise RuntimeError(f"destination must be empty: {destination}")
    ignore = shutil.ignore_patterns(".git", "__pycache__", "*.pyc")
    for item in sorted(source.iterdir()):
        if item.name in {".git", "__pycache__"} or item.suffix == ".pyc":
            continue
        target = destination / item.name
        if item.is_dir():
            _ = shutil.copytree(item, target, ignore=ignore)
        else:
            _ = shutil.copy2(item, target)


def seed_workspace(task_root: Path, run_root: Path) -> str:
    copy_tree(task_root, run_root)
    for command in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "effect-experiment@example.invalid"],
        ["git", "config", "user.name", "Effect Experiment"],
        ["git", "add", "."],
        ["git", "commit", "-qm", "seed"],
    ):
        result = run_checked(command, cwd=run_root, timeout=10)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or f"seed command failed: {command!r}")
    return run_checked(["git", "rev-parse", "HEAD"], cwd=run_root, timeout=10).stdout.strip()


def suite_check(run_root: Path, command: tuple[str, ...], *, timeout: float) -> dict[str, object]:
    try:
        result = run_checked(list(command), cwd=run_root, timeout=timeout)
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
            "stdout": text_output(error.stdout),
            "stderr": text_output(error.stderr),
            "timeout": True,
        }


def changed_paths(run_root: Path, seed_commit: str) -> list[str]:
    changed = run_checked(["git", "diff", "--name-only", "--diff-filter=ACDMRT", seed_commit], cwd=run_root, timeout=10)
    untracked = run_checked(["git", "ls-files", "--others", "--exclude-standard"], cwd=run_root, timeout=10)
    return sorted({line.strip() for line in (changed.stdout + "\n" + untracked.stdout).splitlines() if line.strip()})


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file() and ".git" not in item.parts):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(relative + b"\0" + hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def atomic_write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    _ = temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def copy_skill_snapshot(source: Path, destination: Path) -> Path:
    skill_file = source / "SKILL.md" if source.is_dir() else source
    if skill_file.name != "SKILL.md" or not skill_file.is_file():
        raise ValueError("--skill must name SKILL.md or its containing directory")
    destination.mkdir(parents=True, exist_ok=True)
    snapshot = destination / "SKILL.md"
    _ = shutil.copy2(skill_file, snapshot)
    return snapshot


def score_candidate(
    *,
    run_root: Path,
    task: TaskRecord,
    corpus: Path,
    timeout: float,
) -> dict[str, object]:
    command = [
        sys.executable,
        str(Path(__file__).with_name("score_effect_workspace_v6.py")),
        "--workspace",
        str(run_root),
        "--hidden-root",
        str(corpus / task.hidden_root_path),
        "--command-json",
        json.dumps(list(task.hidden_command)),
        "--timeout",
        str(timeout),
    ]
    try:
        result = subprocess.run(command, env=environment(), capture_output=True, text=True, timeout=timeout + 5, check=False)
        return cast(dict[str, object], json.loads(result.stdout))
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        return {"passed": False, "returncode": None, "stdout": "", "stderr": str(error), "timeout": True}


def execute_condition(
    *,
    task: TaskRecord,
    corpus: Path,
    prompt_path: Path,
    condition: str,
    skill_snapshot: Path,
    raw_root: Path,
    codex_path: str,
    model_id: str,
    harness_id: str,
    agent_timeout: float,
    test_timeout: float,
) -> dict[str, object]:
    artifact_root = raw_root / task.task_id / condition
    artifact_root.mkdir(parents=True, exist_ok=True)
    run_root = Path(tempfile.mkdtemp(prefix=f"adam-effect-v6-{task.task_id}-{condition}-", dir="/tmp"))
    started = time.monotonic()
    agent_exit: int | None = None
    agent_stdout = ""
    agent_stderr = ""
    public: dict[str, object] = {"passed": False, "returncode": None, "stdout": "", "stderr": "not run", "timeout": False}
    hidden: dict[str, object] = {"passed": False, "returncode": None, "stdout": "", "stderr": "not run", "timeout": False}
    paths: list[str] = []
    candidate_digest = ""
    seed_commit = ""
    error: str | None = None
    try:
        seed_commit = seed_workspace(corpus / task.workspace_path, run_root)
        prompt = prompt_path.read_text(encoding="utf-8")
        command = [
            codex_path,
            "exec",
            "-C",
            str(run_root),
            "-m",
            model_id,
            "-s",
            "workspace-write",
            "--ephemeral",
            "--skip-git-repo-check",
            "-o",
            str(artifact_root / "agent-output.md"),
        ]
        if condition == "skill":
            command.extend(["--add-dir", str(skill_snapshot.parent)])
            prompt += f"\nThe supplied Skill path is: {skill_snapshot}."
        command.append(prompt)
        agent_exit, agent_stdout, agent_stderr = run_agent(command, cwd=run_root, timeout=agent_timeout)
        public = suite_check(run_root, task.public_command, timeout=test_timeout)
        paths = changed_paths(run_root, seed_commit)
        hidden = score_candidate(run_root=run_root, task=task, corpus=corpus, timeout=test_timeout)
        candidate_digest = tree_digest(run_root)
    except Exception as caught:  # Preserve diagnostics rather than losing the pair checkpoint.
        error = f"{type(caught).__name__}: {caught}"
        agent_stderr = agent_stderr + ("\n" if agent_stderr else "") + error
        if run_root.exists():
            candidate_digest = tree_digest(run_root)
    finally:
        if run_root.exists():
            if seed_commit:
                diff = run_checked(["git", "diff", seed_commit], cwd=run_root, timeout=10)
                _ = (artifact_root / "candidate.diff").write_text(diff.stdout, encoding="utf-8")
            _ = shutil.rmtree(run_root)
    scope_ok = bool(seed_commit) and set(paths).issubset(set(task.allowed_edit_paths))
    if not scope_ok:
        hidden["passed"] = False
        hidden["scope_violation"] = paths
    _ = (artifact_root / "agent.stdout.log").write_text(agent_stdout, encoding="utf-8")
    _ = (artifact_root / "agent.stderr.log").write_text(agent_stderr, encoding="utf-8")
    _ = (artifact_root / "public.json").write_text(json.dumps(public, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _ = (artifact_root / "hidden-score.json").write_text(json.dumps(hidden, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    elapsed = time.monotonic() - started
    return {
        "condition": condition,
        "model_id": model_id,
        "harness_id": harness_id,
        "agent_exit": agent_exit,
        "public_pass": bool(public.get("passed", False)),
        "trial_complete": agent_exit == 0 and error is None,
        "hidden_repair_pass": agent_exit == 0 and error is None and bool(public.get("passed", False)) and bool(hidden.get("passed", False)) and scope_ok,
        "scope_ok": scope_ok,
        "changed_paths": paths,
        "elapsed_seconds": round(elapsed, 3),
        "artifact_path": str(artifact_root.relative_to(raw_root)),
        "candidate_tree_sha256": candidate_digest,
    }


def execute_task_pair(
    *,
    task: TaskRecord,
    corpus: Path,
    prompts: Path,
    skill_snapshot: Path,
    raw_root: Path,
    arguments: Arguments,
) -> list[dict[str, object]]:
    skill_first = skill_first_for(arguments.seed, task.task_id, 1)
    order = ("skill", "baseline") if skill_first else ("baseline", "skill")
    results: list[dict[str, object]] = []
    for execution_order, condition in enumerate(order, start=1):
        result = execute_condition(
            task=task,
            corpus=corpus,
            prompt_path=prompts / f"{condition}.txt",
            condition=condition,
            skill_snapshot=skill_snapshot,
            raw_root=raw_root,
            codex_path=arguments.codex,
            model_id=arguments.model,
            harness_id=arguments.harness,
            agent_timeout=arguments.agent_timeout,
            test_timeout=arguments.test_timeout,
        )
        result.update({
            "task_id": task.task_id,
            "stratum": task.stratum,
            "execution_order": execution_order,
            "replicate_index": 1,
            "pair_id": f"{task.task_id}-run-1",
        })
        results.append(result)
    return results


def records_for_preregistration(corpus: Mapping[str, object], preregistration: Mapping[str, object]) -> list[TaskRecord]:
    values = corpus.get("tasks")
    if not isinstance(values, list):
        raise ValueError("corpus manifest tasks must be a list")
    by_id = {record.task_id: record for record in (task_from_value(value) for value in cast(list[object], values))}
    plan = preregistration.get("task_plan")
    if not isinstance(plan, dict):
        raise ValueError("preregistration task plan must be a task list")
    plan_value = cast(dict[str, object], plan)
    if not isinstance(plan_value.get("tasks"), list):
        raise ValueError("preregistration task plan must be a task list")
    records: list[TaskRecord] = []
    for value in cast(list[object], plan_value["tasks"]):
        if not isinstance(value, dict):
            raise ValueError("preregistration task has missing task_id or stratum")
        task_value = cast(dict[str, object], value)
        if not isinstance(task_value.get("task_id"), str) or not isinstance(task_value.get("stratum"), str):
            raise ValueError("preregistration task has missing task_id or stratum")
        task_id = cast(str, task_value["task_id"])
        record = by_id.get(task_id)
        if record is None or record.stratum != task_value["stratum"]:
            raise ValueError(f"preregistration task {task_id} differs from corpus manifest")
        records.append(record)
    if set(by_id) != {record.task_id for record in records}:
        raise ValueError("preregistration task plan must contain every corpus task exactly once")
    return records


def validate_preregistration(preregistration: dict[str, object], arguments: Arguments) -> None:
    if preregistration.get("status") != "planned" or preregistration.get("trials") != []:
        raise ValueError("--preregistration must be an unrun planned experiment")
    scope_value = preregistration.get("scope")
    scope = cast(dict[str, object], scope_value) if isinstance(scope_value, dict) else None
    if not isinstance(scope, dict) or scope.get("model_id") != arguments.model or scope.get("harness_id") != arguments.harness:
        raise ValueError("preregistration model or harness does not match runner arguments")
    if len(arguments.preregistration_commit) != 40 or any(character not in "0123456789abcdef" for character in arguments.preregistration_commit.lower()):
        raise ValueError("--preregistration-commit must be a 40-character Git SHA")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("--corpus", type=Path, required=True)
    _ = parser.add_argument("--prompts", type=Path, required=True)
    _ = parser.add_argument("--skill", type=Path, required=True)
    _ = parser.add_argument("--preregistration", type=Path, required=True)
    _ = parser.add_argument("--preregistration-commit", required=True)
    _ = parser.add_argument("--raw-output", type=Path, required=True)
    _ = parser.add_argument("--output", type=Path, required=True)
    _ = parser.add_argument("--seed", type=int, required=True)
    _ = parser.add_argument("--codex", default="codex")
    _ = parser.add_argument("--model", default=DEFAULT_MODEL_ID)
    _ = parser.add_argument("--harness", default=DEFAULT_HARNESS_ID)
    _ = parser.add_argument("--agent-timeout", type=float, default=300.0)
    _ = parser.add_argument("--test-timeout", type=float, default=20.0)
    parsed = cast(dict[str, object], vars(parser.parse_args()))
    arguments = Arguments(
        corpus=cast(Path, parsed["corpus"]),
        prompts=cast(Path, parsed["prompts"]),
        skill=cast(Path, parsed["skill"]),
        preregistration=cast(Path, parsed["preregistration"]),
        preregistration_commit=cast(str, parsed["preregistration_commit"]),
        raw_output=cast(Path, parsed["raw_output"]),
        output=cast(Path, parsed["output"]),
        seed=cast(int, parsed["seed"]),
        codex=cast(str, parsed["codex"]),
        model=cast(str, parsed["model"]),
        harness=cast(str, parsed["harness"]),
        agent_timeout=cast(float, parsed["agent_timeout"]),
        test_timeout=cast(float, parsed["test_timeout"]),
    )
    preregistration = load_json(arguments.preregistration)
    validate_preregistration(preregistration, arguments)
    corpus = load_json(arguments.corpus / "manifest.json")
    tasks = records_for_preregistration(corpus, preregistration)
    arguments.raw_output.mkdir(parents=True, exist_ok=True)
    record = copy.deepcopy(preregistration)
    record["status"] = "collecting"
    record["trials"] = []
    record["preregistration"] = cast(dict[str, object], record["preregistration"]) | {"git_commit": arguments.preregistration_commit}
    record["collection"] = {"checkpointed_after_each_pair": True, "agent_timeout_seconds": arguments.agent_timeout, "test_timeout_seconds": arguments.test_timeout}
    atomic_write_json(arguments.output, record)
    with tempfile.TemporaryDirectory(prefix="adam-effect-v6-skill-") as directory:
        skill_snapshot = copy_skill_snapshot(arguments.skill, Path(directory))
        for task in tasks:
            pair = execute_task_pair(
                task=task,
                corpus=arguments.corpus,
                prompts=arguments.prompts,
                skill_snapshot=skill_snapshot,
                raw_root=arguments.raw_output,
                arguments=arguments,
            )
            trials = cast(list[object], record["trials"])
            trials.extend(pair)
            if not all(bool(result["trial_complete"]) for result in pair):
                record["status"] = "interrupted"
                record["collection"] = cast(dict[str, object], record["collection"]) | {"ineligible_reason": "At least one planned agent condition did not complete; no retry or partial analysis is allowed."}
                atomic_write_json(arguments.output, record)
                return 2
            atomic_write_json(arguments.output, record)
            for result in pair:
                print(json.dumps({key: result[key] for key in ("task_id", "condition", "trial_complete", "hidden_repair_pass", "scope_ok")}), flush=True)
    record["status"] = "completed"
    atomic_write_json(arguments.output, record)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
