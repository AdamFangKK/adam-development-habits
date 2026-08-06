#!/usr/bin/env python3
"""Run a fixed-model paired Codex repair experiment on the held-out corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TypedDict, cast

from analyze_skill_effect import skill_first_for


MODEL_ID = "gpt-5.6-terra"
HARNESS_ID = "codex-cli-0.146.0-alpha.9.2;exec;workspace-write;ephemeral"
CONDITIONS = ("baseline", "skill")


class TaskRecord(TypedDict):
    task_id: str
    stratum: str
    function: str
    source_path: str
    public_cases_path: str
    hidden_cases_path: str


@dataclass(frozen=True)
class EffectArguments:
    corpus: Path
    prompt_dir: Path
    skill: Path
    raw_output: Path
    output: Path
    seed: int
    codex: str
    agent_timeout: float
    max_workers: int
    only_task: str | None


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_checked(command: list[str], *, cwd: Path, timeout: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False)


def _text_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value


def run_agent(command: list[str], *, cwd: Path, timeout: float) -> tuple[int | None, str, str]:
    """Run one agent in a process group so a timeout cannot leak its descendants."""
    environment = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
    }
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        return process.returncode, _text_output(stdout), _text_output(stderr)
    except subprocess.TimeoutExpired as error:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (AttributeError, OSError, ProcessLookupError):
            pass
        stdout, stderr = process.communicate()
        return None, _text_output(stdout or error.stdout), _text_output(stderr or error.stderr) + f"\nagent timeout after {timeout:.1f}s"


def seed_workspace(task_root: Path, run_root: Path) -> str:
    run_root.mkdir(parents=True, exist_ok=True)
    for name in ("buggy.py", "public_cases.json", "test_public.py", "task.md"):
        _ = shutil.copy2(task_root / name, run_root / name)
    _ = run_checked(["git", "init", "-q"], cwd=run_root, timeout=10)
    _ = run_checked(["git", "config", "user.email", "effect-experiment@example.invalid"], cwd=run_root, timeout=10)
    _ = run_checked(["git", "config", "user.name", "Effect Experiment"], cwd=run_root, timeout=10)
    _ = run_checked(["git", "add", "."], cwd=run_root, timeout=10)
    result = run_checked(["git", "commit", "-qm", "seed"], cwd=run_root, timeout=10)
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    head = run_checked(["git", "rev-parse", "HEAD"], cwd=run_root, timeout=10)
    return head.stdout.strip()


def public_check(run_root: Path) -> dict[str, object]:
    try:
        result = subprocess.run(
            [sys.executable, "test_public.py"],
            cwd=run_root,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"},
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        return {
            "passed": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired as error:
        return {"passed": False, "returncode": None, "stdout": error.stdout or "", "stderr": "process timeout"}


def changed_paths(run_root: Path, seed_commit: str) -> list[str]:
    result = run_checked(["git", "diff", "--name-only", seed_commit], cwd=run_root, timeout=10)
    paths = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    status = run_checked(["git", "status", "--short"], cwd=run_root, timeout=10)
    for line in status.stdout.splitlines():
        if line.startswith("?? "):
            paths.append(line[3:].strip())
    return sorted(set(paths))


def execute_condition(
    *,
    task: TaskRecord,
    corpus_root: Path,
    prompt_path: Path,
    condition: str,
    skill_copy: Path,
    raw_root: Path,
    codex_path: str,
    timeout: float,
) -> dict[str, object]:
    task_root = corpus_root / "tasks" / task["task_id"]
    hidden_cases = corpus_root / task["hidden_cases_path"]
    run_root = Path(tempfile.mkdtemp(prefix=f"adam-effect-{task['task_id']}-{condition}-", dir="/tmp"))
    artifact_root = raw_root / task["task_id"] / condition
    artifact_root.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    seed_commit = seed_workspace(task_root, run_root)
    prompt = prompt_path.read_text(encoding="utf-8")
    command = [
        codex_path,
        "exec",
        "-C",
        str(run_root),
        "-m",
        MODEL_ID,
        "-s",
        "workspace-write",
        "--ephemeral",
        "--skip-git-repo-check",
        "-o",
        str(artifact_root / "agent-output.md"),
    ]
    if condition == "skill":
        command.extend(["--add-dir", str(skill_copy)])
        prompt = prompt + f"\nThe supplied Skill path is: {skill_copy / 'SKILL.md'}"
    command.append(prompt)
    agent_exit, agent_stdout, agent_stderr = run_agent(command, cwd=run_root, timeout=timeout)
    public = public_check(run_root)
    paths = changed_paths(run_root, seed_commit)
    scope_ok = paths == ["buggy.py"]
    score_command = [
        sys.executable,
        str(Path(__file__).with_name("score_effect_candidate.py")),
        "--candidate",
        str(run_root / "buggy.py"),
        "--hidden-cases",
        str(hidden_cases),
        "--task-id",
        task["task_id"],
        "--function",
        task["function"],
    ]
    try:
        score = subprocess.run(score_command, capture_output=True, text=True, timeout=20, check=False)
        score_report = cast(dict[str, object], json.loads(score.stdout))
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        score_report = {"passed": False, "error": str(error), "passed_cases": 0, "total_cases": task.get("hidden_case_count", 0)}
    if not scope_ok:
        score_report["passed"] = False
        score_report["scope_violation"] = paths
    _ = (artifact_root / "agent.stdout.log").write_text(agent_stdout, encoding="utf-8")
    _ = (artifact_root / "agent.stderr.log").write_text(agent_stderr, encoding="utf-8")
    diff = run_checked(["git", "diff", seed_commit], cwd=run_root, timeout=10)
    _ = (artifact_root / "candidate.diff").write_text(diff.stdout, encoding="utf-8")
    _ = (artifact_root / "public.json").write_text(json.dumps(public, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _ = (artifact_root / "hidden-score.json").write_text(json.dumps(score_report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    elapsed = time.monotonic() - started
    return {
        "condition": condition,
        "model_id": MODEL_ID,
        "harness_id": HARNESS_ID,
        "agent_exit": agent_exit,
        "public_pass": public.get("passed", False),
        "hidden_repair_pass": bool(score_report.get("passed", False)),
        "scope_ok": scope_ok,
        "changed_paths": paths,
        "elapsed_seconds": round(elapsed, 3),
        "artifact_path": str(artifact_root.relative_to(raw_root)),
        "candidate_sha256": sha256(run_root / "buggy.py"),
    }


def execute_task_pair(
    *,
    task: TaskRecord,
    corpus_root: Path,
    prompt_dir: Path,
    skill_copy: Path,
    raw_root: Path,
    codex_path: str,
    timeout: float,
    seed: int,
) -> list[dict[str, object]]:
    """Run a task's two conditions in the registered order."""
    skill_first = skill_first_for(seed, task["task_id"], 1)
    order = ("skill", "baseline") if skill_first else ("baseline", "skill")
    trials: list[dict[str, object]] = []
    for execution_order, condition in enumerate(order, start=1):
        result = execute_condition(
            task=task,
            corpus_root=corpus_root,
            prompt_path=prompt_dir / f"{condition}.txt",
            condition=condition,
            skill_copy=skill_copy,
            raw_root=raw_root,
            codex_path=codex_path,
            timeout=timeout,
        )
        result.update(
            {
                "task_id": task["task_id"],
                "stratum": task["stratum"],
                "execution_order": execution_order,
                "replicate_index": 1,
                "pair_id": f"{task['task_id']}-run-1",
            }
        )
        trials.append(result)
    return trials


def load_manifest(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("--corpus", type=Path, required=True)
    _ = parser.add_argument("--prompt-dir", type=Path, required=True)
    _ = parser.add_argument("--skill", type=Path, required=True)
    _ = parser.add_argument("--raw-output", type=Path, required=True)
    _ = parser.add_argument("--output", type=Path, required=True)
    _ = parser.add_argument("--seed", type=int, required=True)
    _ = parser.add_argument("--codex", default="codex")
    _ = parser.add_argument("--agent-timeout", type=float, default=180.0)
    _ = parser.add_argument("--max-workers", type=int, default=2)
    _ = parser.add_argument("--only-task")
    parsed = parser.parse_args()
    arguments = EffectArguments(
        corpus=cast(Path, parsed.corpus),
        prompt_dir=cast(Path, parsed.prompt_dir),
        skill=cast(Path, parsed.skill),
        raw_output=cast(Path, parsed.raw_output),
        output=cast(Path, parsed.output),
        seed=cast(int, parsed.seed),
        codex=cast(str, parsed.codex),
        agent_timeout=cast(float, parsed.agent_timeout),
        max_workers=cast(int, parsed.max_workers),
        only_task=cast(Optional[str], parsed.only_task),
    )
    corpus = load_manifest(arguments.corpus / "manifest.json")
    task_records = [cast(TaskRecord, record) for record in cast(list[object], corpus["tasks"])]
    if arguments.only_task is not None:
        task_records = [task for task in task_records if task["task_id"] == arguments.only_task]
        if not task_records:
            raise SystemExit(f"unknown task: {arguments.only_task}")
    arguments.raw_output.mkdir(parents=True, exist_ok=True)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    results: dict[tuple[str, str], dict[str, object]] = {}
    jobs: list[TaskRecord] = task_records
    with ThreadPoolExecutor(max_workers=arguments.max_workers) as pool:
        futures = {
            pool.submit(
                execute_task_pair,
                task=task,
                corpus_root=arguments.corpus,
                prompt_dir=arguments.prompt_dir,
                skill_copy=arguments.skill,
                raw_root=arguments.raw_output,
                codex_path=arguments.codex,
                timeout=arguments.agent_timeout,
                seed=arguments.seed,
            ): task
            for task in jobs
        }
        for future in as_completed(futures):
            task = futures[future]
            pair_results = future.result()
            for result in pair_results:
                results[(task["task_id"], cast(str, result["condition"]))] = result
                print(json.dumps({"task_id": task["task_id"], "condition": result["condition"], "hidden_repair_pass": result["hidden_repair_pass"], "scope_ok": result["scope_ok"]}), flush=True)
    trials: list[dict[str, object]] = []
    for task in task_records:
        skill_first = skill_first_for(arguments.seed, task["task_id"], 1)
        order = ("skill", "baseline") if skill_first else ("baseline", "skill")
        for condition in order:
            trials.append(results[(task["task_id"], condition)] | {"pair_id": f"{task['task_id']}-run-1"})
    corpus_source = cast(dict[str, object], corpus["source"])
    corpus_commit = cast(str, corpus_source["commit"])
    _ = arguments.output.write_text(json.dumps({"trials": trials, "corpus_commit": corpus_commit, "seed": arguments.seed}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
