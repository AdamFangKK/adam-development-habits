#!/usr/bin/env python3
"""Run the frozen V6 cleanup-effect collection through API-key Codex CLI."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from analyze_native_cleanup_effect_v6 import load_object, validate_preregistration
from native_cleanup_effect_runner_v6 import mark_agent_complete, prepare_condition, score_condition


API_AUTH_PREFIX = "Logged in using an API key"
API_KEY_PATTERN = re.compile(r"\bsk-[^\s]+")


def rfc3339_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def redact(value: str) -> str:
    return API_KEY_PATTERN.sub("[REDACTED_API_KEY]", value)


def environment() -> dict[str, str]:
    return {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"}


def checked(command: list[str], *, cwd: Path, timeout: float) -> subprocess.CompletedProcess[str]:
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
        return process.returncode, stdout, stderr
    except subprocess.TimeoutExpired as error:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (AttributeError, OSError, ProcessLookupError):
            pass
        stdout, stderr = process.communicate()
        return None, stdout or cast(str, error.stdout or ""), (stderr or cast(str, error.stderr or "")) + f"\nagent timeout after {timeout:.1f}s"


def build_agent_command(*, codex: str, workspace: Path, model: str, prompt: str) -> list[str]:
    return [
        codex,
        "exec",
        "--disable",
        "skill_search",
        "-C",
        str(workspace),
        "-m",
        model,
        "-s",
        "workspace-write",
        "--ephemeral",
        "--ignore-user-config",
        "--json",
        prompt,
    ]


def require_clean_frozen_source(source_root: Path, preregistration_path: Path) -> None:
    root = source_root.resolve()
    git_root = checked(["git", "rev-parse", "--show-toplevel"], cwd=root, timeout=10)
    if git_root.returncode != 0 or Path(git_root.stdout.strip()).resolve() != root:
        raise ValueError("V6 API collection requires source-root to be a Git worktree root")
    status = checked(["git", "status", "--porcelain", "--untracked-files=all"], cwd=root, timeout=10)
    if status.returncode != 0 or status.stdout.strip():
        raise ValueError("V6 API collection requires a clean frozen Git worktree")
    relative = preregistration_path.resolve().relative_to(root).as_posix()
    head_copy = checked(["git", "show", f"HEAD:{relative}"], cwd=root, timeout=10)
    if head_copy.returncode != 0 or head_copy.stdout.encode("utf-8") != preregistration_path.read_bytes():
        raise ValueError("V6 preregistration must be tracked and identical to the frozen HEAD")


def validate_codex_preflight(*, codex: str, protocol: dict[str, object], model: str) -> None:
    version = cast(str, protocol["codex_cli_version"])
    version_result = checked([codex, "--version"], cwd=Path.cwd(), timeout=15)
    if version_result.returncode != 0 or version_result.stdout.strip() != version:
        raise ValueError("Codex CLI version differs from the frozen V6 runtime")
    auth = checked([codex, "login", "status"], cwd=Path.cwd(), timeout=15)
    auth_text = auth.stdout if auth.stdout.strip() else auth.stderr
    if auth.returncode != 0 or not auth_text.strip().startswith(API_AUTH_PREFIX):
        raise ValueError("Codex authentication mode differs from the frozen V6 API-key runtime")
    timeout = float(cast(int | float, protocol["connectivity_probe_timeout_seconds"]))
    with tempfile.TemporaryDirectory(prefix="adam-native-cleanup-v6-connectivity-", dir="/tmp") as directory:
        workspace = Path(directory)
        exit_code, _, _ = run_agent(
            build_agent_command(
                codex=codex,
                workspace=workspace,
                model=model,
                prompt="Confirm remote Codex connectivity. Do not make changes.",
            ),
            cwd=workspace,
            timeout=timeout,
        )
    if exit_code != 0:
        raise ValueError("Codex agent connectivity probe failed")


def transcript_text(*, exit_code: int | None, stdout: str, stderr: str) -> str:
    return (
        f"executor_exit_code: {exit_code}\n\n"
        f"stdout:\n{redact(stdout)}\n\n"
        f"stderr:\n{redact(stderr)}\n"
    )


def execute_condition(
    *,
    corpus: Path,
    preregistration: Path,
    source_root: Path,
    raw_root: Path,
    task_id: str,
    condition: str,
    codex: str,
    model: str,
    protocol: dict[str, object],
) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix=f"adam-native-cleanup-v6-{task_id}-{condition}-", dir="/tmp") as directory:
        temporary = Path(directory)
        workspace = temporary / "workspace"
        _ = prepare_condition(corpus, preregistration, source_root, raw_root, task_id, condition, workspace)
        prompt = (raw_root / task_id / condition / "agent-prompt.txt").read_text(encoding="utf-8")
        started_at = rfc3339_now()
        exit_code, stdout, stderr = run_agent(
            build_agent_command(codex=codex, workspace=workspace, model=model, prompt=prompt),
            cwd=workspace,
            timeout=float(cast(int | float, protocol["agent_timeout_seconds"])),
        )
        finished_at = rfc3339_now()
        transcript = temporary / "agent-transcript.md"
        _ = transcript.write_text(transcript_text(exit_code=exit_code, stdout=stdout, stderr=stderr), encoding="utf-8")
        mark_agent_complete(
            raw_root,
            task_id,
            condition,
            agent_id=f"codex-cli:{task_id}/{condition}",
            model_id=model,
            started_at=started_at,
            finished_at=finished_at,
            transcript=transcript,
            executor_kind="codex-cli-api-key",
            exit_code=exit_code,
            auth_mode="api-key",
            skill_search_disabled=True,
            codex_cli_version=cast(str, protocol["codex_cli_version"]),
        )
        score = score_condition(corpus, raw_root, task_id, condition, workspace)
        public = score.get("public_result")
        if not isinstance(public, dict) or not isinstance(public.get("passed"), bool):
            raise ValueError("V6 scorer did not produce a boolean public_result.passed")
        return {
            "task_id": task_id,
            "condition": condition,
            "agent_exit_code": exit_code,
            "public_pass": public["passed"],
            "hidden_repair_pass": score["hidden_repair_passed"],
            "implementation_integrity_passed": score["implementation_integrity_passed"],
        }


def collect(*, corpus: Path, preregistration_path: Path, source_root: Path, raw_root: Path, codex: str) -> list[dict[str, object]]:
    if raw_root.exists():
        raise FileExistsError(f"refusing to overwrite V6 raw collection: {raw_root}")
    preregistration = load_object(preregistration_path)
    tasks = validate_preregistration(preregistration, root=source_root.resolve())
    require_clean_frozen_source(source_root, preregistration_path)
    protocol = cast(dict[str, object], preregistration["protocol"])
    model = cast(str, cast(dict[str, object], preregistration["scope"])["model_id"])
    validate_codex_preflight(codex=codex, protocol=protocol, model=model)
    results: list[dict[str, object]] = []
    for task in tasks:
        task_id = cast(str, task["task_id"])
        for condition in cast(list[str], task["execution_order"]):
            result = execute_condition(
                corpus=corpus,
                preregistration=preregistration_path,
                source_root=source_root,
                raw_root=raw_root,
                task_id=task_id,
                condition=condition,
                codex=codex,
                model=model,
                protocol=protocol,
            )
            results.append(result)
            print(json.dumps(result, sort_keys=True), flush=True)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("--corpus", type=Path, required=True)
    _ = parser.add_argument("--preregistration", type=Path, required=True)
    _ = parser.add_argument("--source-root", type=Path, required=True)
    _ = parser.add_argument("--raw-root", type=Path, required=True)
    _ = parser.add_argument("--codex", default=shutil.which("codex") or "codex")
    arguments = parser.parse_args()
    _ = collect(**vars(arguments))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
