#!/usr/bin/env python3
"""Run the checkpointed three-condition V9 Skill-effect protocol."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import signal
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, cast

from analyze_skill_effect_v9 import CONDITIONS, balanced_condition_order, validate_envelope
from audit_effect_isolation_v9 import audit_collection


DEFAULT_MODEL_ID = "gpt-5.6-terra"
DEFAULT_HARNESS_ID = "codex-cli-0.149.0-alpha.4.1;exec-json;workspace-write;ephemeral;skill-search-disabled;absolute-output;condition-checkpointed-v9"
DEFAULT_CODEX = str(Path(__file__).with_name("codex_v9_isolated.py").resolve())
REAL_CODEX = Path("/Applications/ChatGPT.app/Contents/Resources/codex")
CODEX_VERSION = "0.149.0-alpha.4.1"
CODEX_AUTH_STATUS_PREFIX = {
    "api-key": "Logged in using an API key",
    "chatgpt": "Logged in using ChatGPT",
}
CONNECTIVITY_PROBE_TIMEOUT_SECONDS = 60.0
API_KEY_PATTERN = re.compile(r"\bsk-[^\s]+")


@dataclass(frozen=True)
class TaskRecord:
    task_id: str
    cohort: str
    stratum: str
    workspace_path: str
    hidden_tests_path: str
    allowed_edit_paths: tuple[str, ...]
    public_command: tuple[str, ...]
    hidden_command: tuple[str, ...]
    execution_order: tuple[str, ...] = ()


@dataclass(frozen=True)
class Arguments:
    corpus: Path
    prompts: Path
    old_skill: Path
    new_skill: Path
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
    preflight: bool


def text_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value


def redact_sensitive_text(value: str) -> str:
    return API_KEY_PATTERN.sub("[REDACTED_API_KEY]", value)


def redact_sensitive_value(value: object) -> object:
    if isinstance(value, str):
        return redact_sensitive_text(value)
    if isinstance(value, list):
        return [redact_sensitive_value(item) for item in value]
    if isinstance(value, dict):
        return {key: redact_sensitive_value(item) for key, item in value.items()}
    return value


def environment() -> dict[str, str]:
    return {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "ADAM_V9_CODEX_BINARY": str(REAL_CODEX),
    }


def run_checked(command: list[str], *, cwd: Path, timeout: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, env=environment(), capture_output=True, text=True, timeout=timeout, check=False)


def run_agent(command: list[str], *, cwd: Path, timeout: float) -> tuple[int | None, str, str]:
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


def load_json(path: Path) -> dict[str, object]:
    value = cast(object, json.loads(path.read_text(encoding="utf-8")))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return cast(dict[str, object], value)


def sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"hash input must be a regular file: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command_value(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a non-empty list of non-empty strings")
    parts = cast(list[object], value)
    if not parts or any(not isinstance(part, str) or not part for part in parts):
        raise ValueError(f"{field} must be a non-empty list of non-empty strings")
    return tuple(part for part in parts if isinstance(part, str))


def path_values(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a non-empty list of relative paths")
    parts = cast(list[object], value)
    if not parts or any(
        not isinstance(part, str)
        or not part
        or Path(part).is_absolute()
        or ".." in Path(part).parts
        for part in parts
    ):
        raise ValueError(f"{field} must be a non-empty list of safe relative paths")
    return tuple(part for part in parts if isinstance(part, str))


def safe_relative_path(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or Path(value).is_absolute() or ".." in Path(value).parts:
        raise ValueError(f"{field} must be a safe relative path")
    return value


def task_from_value(value: object) -> TaskRecord:
    if not isinstance(value, dict):
        raise ValueError("manifest task must be an object")
    task = cast(dict[str, object], value)
    for field in ("task_id", "cohort", "stratum", "workspace_path", "hidden_tests_path"):
        if not isinstance(task.get(field), str) or not str(task[field]).strip():
            raise ValueError("manifest task has missing text fields")
    task_id = cast(str, task["task_id"])
    if Path(task_id).name != task_id or task_id in {".", ".."}:
        raise ValueError("manifest task_id must be one safe path segment")
    return TaskRecord(
        task_id=task_id,
        cohort=cast(str, task["cohort"]),
        stratum=cast(str, task["stratum"]),
        workspace_path=safe_relative_path(task["workspace_path"], "workspace_path"),
        hidden_tests_path=safe_relative_path(task["hidden_tests_path"], "hidden_tests_path"),
        allowed_edit_paths=path_values(task.get("allowed_edit_paths"), "allowed_edit_paths"),
        public_command=command_value(task.get("public_command"), "public_command"),
        hidden_command=command_value(task.get("hidden_command"), "hidden_command"),
    )


def copy_tree(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    if any(destination.iterdir()):
        raise RuntimeError(f"destination must be empty: {destination}")
    ignore = shutil.ignore_patterns(".git", "__pycache__", "*.pyc")
    for item in sorted(source.iterdir()):
        if item.name in {".git", "__pycache__"} or item.suffix == ".pyc":
            continue
        target = destination / item.name
        if item.is_symlink():
            raise ValueError(f"workspace source must not contain symbolic links: {item}")
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
        if path.is_symlink():
            raise ValueError(f"candidate tree must not contain symbolic links: {path}")
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(relative + b"\0" + hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def git_root(path: Path) -> Path:
    result = subprocess.run(
        ["git", "-C", str(path.parent), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError("preregistration must be inside a Git worktree")
    return Path(result.stdout.strip()).resolve()


def frozen_protocol_files() -> tuple[Path, ...]:
    directory = Path(__file__).resolve().parent
    return tuple(
        directory / name
        for name in (
            "run_effect_experiment_v9.py",
            "score_effect_workspace_v9.py",
            "analyze_skill_effect_v9.py",
            "audit_effect_isolation_v9.py",
            "materialize_effect_corpus_v9.py",
            "create_effect_preregistration_v9.py",
            "generate_effect_artifact_manifest_v9.py",
            "codex_v9_isolated.py",
        )
    )


def frozen_relative_path(root: Path, path: Path) -> Path:
    absolute = Path(os.path.abspath(path))
    try:
        relative = absolute.relative_to(root)
    except ValueError as error:
        raise ValueError(f"frozen V9 input is outside the collection worktree: {path}") from error
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ValueError(f"frozen V9 input contains a symbolic link: {current}")
    if not absolute.exists():
        raise ValueError(f"frozen V9 input does not exist: {absolute}")
    return relative


def validate_frozen_worktree(arguments: Arguments, preregistration: Mapping[str, object]) -> Path:
    root = git_root(arguments.preregistration)
    status = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all"],
        capture_output=True,
        text=True,
        check=False,
    )
    if status.returncode != 0 or status.stdout.strip():
        raise ValueError("V9 collection requires a clean Git worktree")
    head = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    if head != arguments.preregistration_commit:
        raise ValueError("--preregistration-commit must equal the clean worktree HEAD")
    relative = arguments.preregistration.resolve().relative_to(root).as_posix()
    committed = subprocess.run(
        ["git", "-C", str(root), "show", f"{head}:{relative}"], capture_output=True, check=False
    )
    if committed.returncode != 0 or committed.stdout != arguments.preregistration.read_bytes():
        raise ValueError("preregistration bytes differ from the frozen commit")

    metadata = preregistration.get("preregistration")
    input_commit = cast(dict[str, object], metadata).get("git_commit") if isinstance(metadata, dict) else None
    if not isinstance(input_commit, str) or len(input_commit) != 40 or input_commit != input_commit.lower() or any(
        character not in "0123456789abcdef" for character in input_commit
    ):
        raise ValueError("preregistration.git_commit must bind the frozen input commit")
    exists = subprocess.run(
        ["git", "-C", str(root), "cat-file", "-e", f"{input_commit}^{{commit}}"],
        capture_output=True,
        check=False,
    )
    if exists.returncode != 0:
        raise ValueError("preregistration.git_commit is not available in the collection repository")
    changed = subprocess.run(
        ["git", "-C", str(root), "diff", "--name-only", input_commit, head],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    if changed != [relative]:
        raise ValueError("only the preregistration file may differ from the frozen input commit")

    input_files = list(frozen_protocol_files()) + [
        skill_file(arguments.old_skill),
        skill_file(arguments.new_skill),
        arguments.preregistration,
    ]
    for directory in (arguments.corpus, arguments.prompts):
        _ = frozen_relative_path(root, directory)
        input_files.extend(path for path in directory.rglob("*") if path.is_file() or path.is_symlink())
    tracked = set(
        subprocess.run(
            ["git", "-C", str(root), "ls-tree", "-r", "--name-only", head],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
    )
    for path in input_files:
        frozen_relative = frozen_relative_path(root, path).as_posix()
        if not path.is_file() or frozen_relative not in tracked:
            raise ValueError(f"frozen V9 input is not a tracked regular file: {path}")
    return root


def validated_auth_mode(value: object) -> str:
    if not isinstance(value, str) or value not in CODEX_AUTH_STATUS_PREFIX:
        raise ValueError("Codex authentication mode differs from the frozen V9 runtime")
    return value


def authenticated_status_matches(auth_mode: str, status: str) -> bool:
    expected = CODEX_AUTH_STATUS_PREFIX[auth_mode]
    normalized = status.strip()
    return normalized.startswith(expected) if auth_mode == "api-key" else normalized == expected


def authentication_status(auth: subprocess.CompletedProcess[str]) -> str:
    return auth.stdout if auth.stdout.strip() else auth.stderr


def validate_codex_version(auth_mode: str) -> None:
    auth_mode = validated_auth_mode(auth_mode)
    if not REAL_CODEX.is_file() or REAL_CODEX.is_symlink():
        raise ValueError(f"frozen Codex binary is missing or unsafe: {REAL_CODEX}")
    result = subprocess.run([str(REAL_CODEX), "--version"], capture_output=True, text=True, check=False)
    if result.returncode != 0 or result.stdout.strip() != f"codex-cli {CODEX_VERSION}":
        raise ValueError("Codex version differs from the frozen V9 runtime")
    auth = subprocess.run(
        [str(REAL_CODEX), "login", "status"],
        capture_output=True,
        text=True,
        check=False,
    )
    if auth.returncode != 0 or not authenticated_status_matches(auth_mode, authentication_status(auth)):
        raise ValueError("Codex authentication mode differs from the frozen V9 runtime")


def validate_agent_connectivity(arguments: Arguments) -> None:
    with tempfile.TemporaryDirectory(prefix="adam-effect-v9-connectivity-", dir="/tmp") as directory:
        workspace = Path(directory)
        command = [
            arguments.codex,
            "exec",
            "-C",
            str(workspace),
            "-m",
            arguments.model,
            "-s",
            "workspace-write",
            "--ephemeral",
            "--skip-git-repo-check",
            "--ignore-user-config",
            "--json",
            "-o",
            str(workspace / "connectivity-output.md"),
            "Confirm remote Codex connectivity. Do not make changes.",
        ]
        agent_exit, _, _ = run_agent(
            command,
            cwd=workspace,
            timeout=min(arguments.agent_timeout, CONNECTIVITY_PROBE_TIMEOUT_SECONDS),
        )
    if agent_exit != 0:
        raise ValueError("Codex agent connectivity probe failed")


def validate_corpus_trees(corpus_root: Path, manifest: Mapping[str, object]) -> None:
    values = manifest.get("tasks")
    if not isinstance(values, list):
        raise ValueError("corpus manifest tasks must be a list")
    for value in cast(list[object], values):
        if not isinstance(value, dict):
            raise ValueError("corpus manifest task must be an object")
        task = cast(dict[str, object], value)
        for path_field, digest_field in (
            ("workspace_path", "workspace_tree_sha256"),
            ("hidden_tests_path", "hidden_tests_tree_sha256"),
            ("reference_path", "reference_tree_sha256"),
        ):
            relative = task.get(path_field)
            expected = task.get(digest_field)
            if not isinstance(relative, str) or not isinstance(expected, str):
                raise ValueError(f"corpus task is missing {path_field} or {digest_field}")
            if tree_digest(corpus_root / relative) != expected:
                raise ValueError(f"corpus tree hash differs for {relative}")


def atomic_write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    _ = temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def skill_file(source: Path) -> Path:
    skill = source / "SKILL.md" if source.is_dir() else source
    if skill.name != "SKILL.md" or not skill.is_file() or skill.is_symlink():
        raise ValueError("Skill input must name SKILL.md or its containing directory")
    return skill


def copy_skill_snapshot(source: Path, destination: Path) -> Path:
    skill = skill_file(source)
    destination.mkdir(parents=True, exist_ok=True)
    snapshot = destination / "SKILL.md"
    _ = shutil.copy2(skill, snapshot)
    return snapshot


def score_candidate(*, run_root: Path, task: TaskRecord, corpus: Path, timeout: float) -> dict[str, object]:
    command = [
        sys.executable,
        str(Path(__file__).with_name("score_effect_workspace_v9.py")),
        "--workspace",
        str(run_root),
        "--hidden-root",
        str(corpus / task.hidden_tests_path),
        "--allowed-paths-json",
        json.dumps(list(task.allowed_edit_paths)),
        "--command-json",
        json.dumps(list(task.hidden_command)),
        "--timeout",
        str(timeout),
    ]
    try:
        result = subprocess.run(command, env=environment(), capture_output=True, text=True, timeout=timeout + 5, check=False)
        report = cast(object, json.loads(result.stdout))
        if not isinstance(report, dict):
            raise ValueError("hidden scorer did not return an object")
        return cast(dict[str, object], report)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, ValueError) as error:
        return {
            "passed": False,
            "returncode": None,
            "stdout": "",
            "stderr": str(error),
            "timeout": True,
            "implementation_integrity_passed": False,
        }


def prompt_for_condition(prompts: Path, condition: str, snapshot: Path | None) -> str:
    prompt = (prompts / f"{condition}.txt").read_text(encoding="utf-8")
    if snapshot is None:
        return prompt
    return prompt.format(skill_path=str(snapshot))


def execute_condition(
    *,
    task: TaskRecord,
    corpus: Path,
    prompts: Path,
    condition: str,
    skill_snapshots: Mapping[str, Path],
    raw_root: Path,
    codex_path: str,
    model_id: str,
    harness_id: str,
    agent_timeout: float,
    test_timeout: float,
) -> dict[str, object]:
    artifact_root = raw_root / task.task_id / condition
    if artifact_root.exists():
        raise FileExistsError(f"refusing to overwrite trial artifact: {artifact_root}")
    artifact_root.mkdir(parents=True)
    run_root = Path(tempfile.mkdtemp(prefix=f"adam-effect-v9-{task.task_id}-{condition}-", dir="/tmp"))
    started = time.monotonic()
    agent_exit: int | None = None
    agent_stdout = ""
    agent_stderr = ""
    public: dict[str, object] = {"passed": False, "returncode": None, "stdout": "", "stderr": "not run", "timeout": False}
    hidden: dict[str, object] = {
        "passed": False,
        "returncode": None,
        "stdout": "",
        "stderr": "not run",
        "timeout": False,
        "implementation_integrity_passed": False,
    }
    paths: list[str] = []
    candidate_digest = ""
    snapshot_before = ""
    snapshot_after = ""
    seed_commit = ""
    error: str | None = None
    snapshot = skill_snapshots.get(condition)
    try:
        seed_commit = seed_workspace(corpus / task.workspace_path, run_root)
        if snapshot is not None:
            snapshot_before = sha256(snapshot)
        prompt = prompt_for_condition(prompts, condition, snapshot)
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
            "--ignore-user-config",
            "--json",
            "-o",
            str(artifact_root / "agent-output.md"),
        ]
        command.append(prompt)
        agent_exit, agent_stdout, agent_stderr = run_agent(command, cwd=run_root, timeout=agent_timeout)
        if snapshot is not None:
            snapshot_after = sha256(snapshot)
        public = suite_check(run_root, task.public_command, timeout=test_timeout)
        paths = changed_paths(run_root, seed_commit)
        hidden = score_candidate(run_root=run_root, task=task, corpus=corpus, timeout=test_timeout)
        candidate_digest = tree_digest(run_root)
    except Exception as caught:
        error = f"{type(caught).__name__}: {caught}"
        agent_stderr = agent_stderr + ("\n" if agent_stderr else "") + error
        if run_root.exists():
            candidate_digest = tree_digest(run_root)
    finally:
        if run_root.exists():
            if seed_commit:
                diff = run_checked(["git", "diff", seed_commit], cwd=run_root, timeout=10)
                _ = (artifact_root / "candidate.diff").write_text(redact_sensitive_text(diff.stdout), encoding="utf-8")
            elif not (artifact_root / "candidate.diff").exists():
                _ = (artifact_root / "candidate.diff").write_text("", encoding="utf-8")
            _ = shutil.rmtree(run_root)
    scope_ok = bool(seed_commit) and set(paths).issubset(set(task.allowed_edit_paths))
    if not scope_ok:
        hidden["passed"] = False
        hidden["scope_violation"] = paths
    agent_output = artifact_root / "agent-output.md"
    agent_output_present = agent_output.is_file()
    output_text = agent_output.read_text(encoding="utf-8") if agent_output_present else ""
    _ = agent_output.write_text(redact_sensitive_text(output_text), encoding="utf-8")
    agent_stdout = redact_sensitive_text(agent_stdout)
    agent_stderr = redact_sensitive_text(agent_stderr)
    public = cast(dict[str, object], redact_sensitive_value(public))
    hidden = cast(dict[str, object], redact_sensitive_value(hidden))
    _ = (artifact_root / "agent.stdout.log").write_text(agent_stdout, encoding="utf-8")
    _ = (artifact_root / "agent.stderr.log").write_text(agent_stderr, encoding="utf-8")
    _ = (artifact_root / "public.json").write_text(json.dumps(public, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _ = (artifact_root / "hidden-score.json").write_text(json.dumps(hidden, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    elapsed = time.monotonic() - started
    integrity = bool(hidden.get("implementation_integrity_passed", False))
    snapshot_integrity = snapshot is None or bool(snapshot_before) and snapshot_before == snapshot_after
    trial_complete = agent_exit == 0 and error is None
    return {
        "condition": condition,
        "model_id": model_id,
        "harness_id": harness_id,
        "agent_exit": agent_exit,
        "public_pass": bool(public.get("passed", False)),
        "trial_complete": trial_complete,
        "hidden_repair_pass": trial_complete and bool(public.get("passed", False)) and bool(hidden.get("passed", False)) and scope_ok and snapshot_integrity,
        "hidden_scorer_pass": bool(hidden.get("passed", False)),
        "implementation_integrity_passed": integrity,
        "skill_snapshot_integrity_passed": snapshot_integrity,
        "skill_snapshot_sha256": snapshot_before or None,
        "scope_ok": scope_ok,
        "changed_paths": paths,
        "elapsed_seconds": round(elapsed, 3),
        "artifact_path": str(artifact_root.relative_to(raw_root)),
        "candidate_tree_sha256": candidate_digest,
        "agent_output_present": agent_output_present,
    }


def execute_task_block(
    *,
    task: TaskRecord,
    corpus: Path,
    prompts: Path,
    skill_snapshots: Mapping[str, Path],
    raw_root: Path,
    arguments: Arguments,
    on_trial_start: Callable[[dict[str, object]], None] | None = None,
    on_trial_complete: Callable[[dict[str, object]], None] | None = None,
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    order = task.execution_order or tuple(CONDITIONS)
    for execution_order, condition in enumerate(order, start=1):
        identity = {
            "block_id": f"{task.task_id}-run-1",
            "task_id": task.task_id,
            "cohort": task.cohort,
            "stratum": task.stratum,
            "condition": condition,
            "execution_order": execution_order,
            "replicate_index": 1,
        }
        pending: dict[str, object] = {
            **identity,
            "model_id": arguments.model,
            "harness_id": arguments.harness,
            "trial_complete": False,
            "hidden_repair_pass": False,
            "hidden_scorer_pass": False,
            "implementation_integrity_passed": False,
            "skill_snapshot_integrity_passed": condition == "no_skill",
            "scope_ok": False,
            "artifact_path": f"{task.task_id}/{condition}",
            "collection_status": "started",
        }
        if on_trial_start is not None:
            on_trial_start(pending)
        result = execute_condition(
            task=task,
            corpus=corpus,
            prompts=prompts,
            condition=condition,
            skill_snapshots=skill_snapshots,
            raw_root=raw_root,
            codex_path=arguments.codex,
            model_id=arguments.model,
            harness_id=arguments.harness,
            agent_timeout=arguments.agent_timeout,
            test_timeout=arguments.test_timeout,
        )
        result.update(identity | {"collection_status": "completed"})
        if on_trial_complete is not None:
            on_trial_complete(result)
        results.append(result)
    return results


def records_for_preregistration(corpus: Mapping[str, object], preregistration: Mapping[str, object]) -> list[TaskRecord]:
    values = corpus.get("tasks")
    if not isinstance(values, list):
        raise ValueError("corpus manifest tasks must be a list")
    by_id = {record.task_id: record for record in (task_from_value(value) for value in cast(list[object], values))}
    plan = preregistration.get("task_plan")
    if not isinstance(plan, dict) or not isinstance(plan.get("tasks"), list):
        raise ValueError("preregistration task plan must be a task list")
    records: list[TaskRecord] = []
    seen: set[str] = set()
    analysis = preregistration.get("analysis")
    seed = cast(dict[str, object], analysis).get("random_seed") if isinstance(analysis, dict) else None
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("preregistration analysis.random_seed must be an integer")
    for index, value in enumerate(cast(list[object], plan["tasks"])):
        if not isinstance(value, dict):
            raise ValueError("preregistration task has missing task_id, cohort, or stratum")
        task = cast(dict[str, object], value)
        if not all(isinstance(task.get(field), str) for field in ("task_id", "cohort", "stratum")):
            raise ValueError("preregistration task has missing task_id, cohort, or stratum")
        task_id = cast(str, task["task_id"])
        if task_id in seen:
            raise ValueError(f"duplicate preregistered task {task_id}")
        seen.add(task_id)
        record = by_id.get(task_id)
        if record is None or record.cohort != task["cohort"] or record.stratum != task["stratum"]:
            raise ValueError(f"preregistration task {task_id} differs from corpus manifest")
        order = command_value(task.get("execution_order"), "execution_order")
        if order != balanced_condition_order(seed, index):
            raise ValueError(f"preregistration task {task_id} has a non-balanced execution order")
        records.append(TaskRecord(
            task_id=record.task_id,
            cohort=record.cohort,
            stratum=record.stratum,
            workspace_path=record.workspace_path,
            hidden_tests_path=record.hidden_tests_path,
            allowed_edit_paths=record.allowed_edit_paths,
            public_command=record.public_command,
            hidden_command=record.hidden_command,
            execution_order=order,
        ))
    if set(by_id) != seen:
        raise ValueError("preregistration task plan must contain every corpus task exactly once")
    return records


def validate_preregistration(preregistration: dict[str, object], arguments: Arguments) -> None:
    if preregistration.get("schema_version") != 2 or preregistration.get("status") != "planned" or preregistration.get("trials") != []:
        raise ValueError("--preregistration must be an unrun planned experiment")
    validate_envelope(preregistration)
    scope_value = preregistration.get("scope")
    scope = cast(dict[str, object], scope_value) if isinstance(scope_value, dict) else None
    if not isinstance(scope, dict) or scope.get("model_id") != arguments.model or scope.get("harness_id") != arguments.harness:
        raise ValueError("preregistration model or harness does not match runner arguments")
    if len(arguments.preregistration_commit) != 40 or any(character not in "0123456789abcdef" for character in arguments.preregistration_commit.lower()):
        raise ValueError("--preregistration-commit must be a 40-character Git SHA")
    frozen_wrapper = Path(__file__).with_name("codex_v9_isolated.py").resolve()
    if Path(arguments.codex).resolve() != frozen_wrapper:
        raise ValueError("--codex must use the frozen V9 isolation wrapper")
    if not os.access(frozen_wrapper, os.X_OK):
        raise ValueError("frozen V9 isolation wrapper is not executable")
    protocol_value = preregistration.get("protocol")
    protocol = cast(dict[str, object], protocol_value) if isinstance(protocol_value, dict) else None
    if not isinstance(protocol, dict):
        raise ValueError("--preregistration must contain protocol hashes")
    analysis_value = preregistration.get("analysis")
    analysis = cast(dict[str, object], analysis_value) if isinstance(analysis_value, dict) else None
    if not isinstance(analysis, dict) or analysis.get("random_seed") != arguments.seed:
        raise ValueError("random seed differs from preregistration")
    if protocol.get("agent_timeout_seconds") != arguments.agent_timeout or protocol.get("test_timeout_seconds") != arguments.test_timeout:
        raise ValueError("timeouts differ from preregistration")
    if protocol.get("connectivity_probe_timeout_seconds") != CONNECTIVITY_PROBE_TIMEOUT_SECONDS:
        raise ValueError("connectivity probe timeout differs from preregistration")
    if protocol.get("conditions") != list(CONDITIONS):
        raise ValueError("conditions differ from preregistration")
    if protocol.get("codex_cli_version") != f"codex-cli {CODEX_VERSION}":
        raise ValueError("Codex CLI version differs from preregistration")
    _ = validated_auth_mode(protocol.get("codex_auth_mode"))
    expected = {
        "old_skill_sha256": sha256(skill_file(arguments.old_skill)),
        "new_skill_sha256": sha256(skill_file(arguments.new_skill)),
        "baseline_prompt_sha256": sha256(arguments.prompts / "no_skill.txt"),
        "old_skill_prompt_sha256": sha256(arguments.prompts / "old_skill.txt"),
        "new_skill_prompt_sha256": sha256(arguments.prompts / "new_skill.txt"),
        "corpus_manifest_sha256": sha256(arguments.corpus / "manifest.json"),
        "runner_sha256": sha256(Path(__file__).resolve()),
        "hidden_scorer_sha256": sha256(Path(__file__).with_name("score_effect_workspace_v9.py")),
        "analyzer_sha256": sha256(Path(__file__).with_name("analyze_skill_effect_v9.py")),
        "isolation_auditor_sha256": sha256(Path(__file__).with_name("audit_effect_isolation_v9.py")),
        "generator_sha256": sha256(Path(__file__).with_name("materialize_effect_corpus_v9.py")),
        "preregistration_generator_sha256": sha256(Path(__file__).with_name("create_effect_preregistration_v9.py")),
        "artifact_manifest_generator_sha256": sha256(Path(__file__).with_name("generate_effect_artifact_manifest_v9.py")),
        "codex_wrapper_sha256": sha256(Path(__file__).with_name("codex_v9_isolated.py")),
    }
    for field, actual in expected.items():
        if protocol.get(field) != actual:
            raise ValueError(f"{field} differs from preregistration")


def validate_empty_outputs(raw_output: Path, output: Path) -> None:
    if raw_output == output or raw_output in output.parents:
        raise ValueError("--output must be outside --raw-output")
    if raw_output.is_symlink() or output.is_symlink():
        raise ValueError("collection outputs must not be symbolic links")
    if raw_output.exists():
        raise ValueError("--raw-output must be new")
    if output.exists():
        raise ValueError("--output must be a new result path")


def parse_arguments() -> Arguments:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("--corpus", type=Path, required=True)
    _ = parser.add_argument("--prompts", type=Path, required=True)
    _ = parser.add_argument("--old-skill", type=Path, required=True)
    _ = parser.add_argument("--new-skill", type=Path, required=True)
    _ = parser.add_argument("--preregistration", type=Path, required=True)
    _ = parser.add_argument("--preregistration-commit", required=True)
    _ = parser.add_argument("--raw-output", type=Path, required=True)
    _ = parser.add_argument("--output", type=Path, required=True)
    _ = parser.add_argument("--seed", type=int, required=True)
    _ = parser.add_argument("--codex", default=DEFAULT_CODEX)
    _ = parser.add_argument("--model", default=DEFAULT_MODEL_ID)
    _ = parser.add_argument("--harness", default=DEFAULT_HARNESS_ID)
    _ = parser.add_argument("--agent-timeout", type=float, default=420.0)
    _ = parser.add_argument("--test-timeout", type=float, default=30.0)
    _ = parser.add_argument("--preflight", action="store_true")
    parsed = cast(dict[str, object], vars(parser.parse_args()))
    return Arguments(
        corpus=cast(Path, parsed["corpus"]),
        prompts=cast(Path, parsed["prompts"]),
        old_skill=cast(Path, parsed["old_skill"]),
        new_skill=cast(Path, parsed["new_skill"]),
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
        preflight=cast(bool, parsed["preflight"]),
    )


def main() -> int:
    arguments = parse_arguments()
    preregistration = load_json(arguments.preregistration)
    validate_preregistration(preregistration, arguments)
    validate_empty_outputs(arguments.raw_output, arguments.output)
    corpus = load_json(arguments.corpus / "manifest.json")
    validate_corpus_trees(arguments.corpus, corpus)
    tasks = records_for_preregistration(corpus, preregistration)
    _ = validate_frozen_worktree(arguments, preregistration)
    protocol = cast(dict[str, object], preregistration["protocol"])
    validate_codex_version(validated_auth_mode(protocol.get("codex_auth_mode")))
    validate_agent_connectivity(arguments)
    if arguments.preflight:
        print("V9 preflight passed")
        return 0

    arguments.raw_output.mkdir(parents=True, exist_ok=True)
    record = copy.deepcopy(preregistration)
    record["status"] = "collecting"
    record["trials"] = []
    record["preregistration"] = cast(dict[str, object], record["preregistration"]) | {
        "collection_git_commit": arguments.preregistration_commit
    }
    record["collection"] = {
        "checkpointed_after_each_block": True,
        "agent_timeout_seconds": arguments.agent_timeout,
        "test_timeout_seconds": arguments.test_timeout,
        "isolation_audit_passed": False,
    }
    atomic_write_json(arguments.output, record)
    snapshots = {
        "old_skill": skill_file(arguments.old_skill).resolve(),
        "new_skill": skill_file(arguments.new_skill).resolve(),
    }

    def checkpoint_started(trial: dict[str, object]) -> None:
        cast(list[object], record["trials"]).append(trial)
        atomic_write_json(arguments.output, record)

    def checkpoint_completed(trial: dict[str, object]) -> None:
        trials = cast(list[object], record["trials"])
        matches = [
            index
            for index, value in enumerate(trials)
            if isinstance(value, dict)
            and value.get("block_id") == trial.get("block_id")
            and value.get("condition") == trial.get("condition")
        ]
        if len(matches) != 1:
            raise RuntimeError("completed V9 trial does not match exactly one started checkpoint")
        trials[matches[0]] = trial
        atomic_write_json(arguments.output, record)

    try:
        for task in tasks:
            block = execute_task_block(
                task=task,
                corpus=arguments.corpus,
                prompts=arguments.prompts,
                skill_snapshots=snapshots,
                raw_root=arguments.raw_output,
                arguments=arguments,
                on_trial_start=checkpoint_started,
                on_trial_complete=checkpoint_completed,
            )
            if not all(bool(result["trial_complete"]) for result in block):
                record["status"] = "interrupted"
                record["collection"] = cast(dict[str, object], record["collection"]) | {
                    "ineligible_reason": "At least one planned V9 condition did not complete; no retry or partial analysis is allowed."
                }
                atomic_write_json(arguments.output, record)
                return 2
            atomic_write_json(arguments.output, record)
            for result in block:
                print(
                    json.dumps({
                        key: result[key]
                        for key in ("task_id", "condition", "trial_complete", "hidden_repair_pass", "scope_ok")
                    }),
                    flush=True,
                )
    except BaseException as caught:
        record["status"] = "interrupted"
        record["collection"] = cast(dict[str, object], record["collection"]) | {
            "ineligible_reason": "V9 collection raised after a started checkpoint; no retry or partial analysis is allowed.",
            "interruption": f"{type(caught).__name__}: {caught}",
        }
        atomic_write_json(arguments.output, record)
        raise
    record["status"] = "completed"
    atomic_write_json(arguments.output, record)
    try:
        audit = audit_collection(
            arguments.raw_output,
            arguments.output,
            old_skill=snapshots["old_skill"],
            new_skill=snapshots["new_skill"],
            corpus=arguments.corpus,
        )
    except Exception as caught:
        audit = {
            "passed": False,
            "failures": [f"isolation audit raised {type(caught).__name__}: {caught}"],
        }
    _ = (arguments.raw_output / "isolation-audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    audit_passed = audit.get("passed") is True
    record["collection"] = cast(dict[str, object], record["collection"]) | {
        "analysis_eligibility": "eligible" if audit_passed else "ineligible",
        "isolation_audit_passed": audit_passed,
        "isolation_audit": audit,
    }
    if not audit_passed:
        record["status"] = "interrupted"
    atomic_write_json(arguments.output, record)
    return 0 if audit_passed else 3


if __name__ == "__main__":
    raise SystemExit(main())
