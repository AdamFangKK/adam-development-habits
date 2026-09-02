#!/usr/bin/env python3
"""Execute V6 native cleanup-effect conditions with a predecessor-score chain."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from native_cleanup_effect_runner_v1 import copy_public_tree, manifest_task, score_trial


CONDITIONS = ("no_skill", "old_skill", "new_skill")
PREPARE_ARTIFACTS = {"sequence.json", "prepare.json", "seed.txt", "agent-prompt.txt"}
FINAL_ARTIFACTS = PREPARE_ARTIFACTS | {"agent-result.json", "agent-transcript.md", "candidate.diff", "score.json"}
EXECUTOR_KINDS = ("codex-native-subagent", "codex-cli-api-key")


@dataclass(frozen=True)
class PreparedCondition:
    task_id: str
    condition: str
    seed_commit: str
    predecessor_score_sha256: tuple[dict[str, str], ...]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return cast(dict[str, object], value)


def run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)


def untracked_paths(workspace: Path) -> list[str]:
    result = run(["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=workspace)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "cannot list untracked candidate files")
    return sorted(path for path in result.stdout.split("\0") if path)


def capture_candidate_diff(workspace: Path, seed_commit: str) -> str:
    """Return a replayable binary diff that includes untracked candidate files."""
    paths = untracked_paths(workspace)
    if paths:
        pathspec = "\0".join(paths) + "\0"
        intent = subprocess.run(
            ["git", "add", "--intent-to-add", "--pathspec-from-file=-", "--pathspec-file-nul"],
            cwd=workspace,
            input=pathspec,
            capture_output=True,
            text=True,
            check=False,
        )
        if intent.returncode != 0:
            raise RuntimeError(intent.stderr.strip() or "cannot add untracked candidate files to the diff index")
    result = run(["git", "diff", "--binary", seed_commit], cwd=workspace)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "cannot write candidate diff")
    return result.stdout


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
    agent = load_json(directory / "agent-result.json")
    if agent.get("status") != "agent_exited":
        raise ValueError(f"predecessor {condition} lacks a completed native-agent record")
    if score.get("scored_after_agent_exit") is not True:
        raise ValueError(f"predecessor {condition} was not scored after agent exit")
    return {"condition": condition, "sha256": sha256(score_path)}


def write_json(path: Path, value: dict[str, object]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def workspace_input_sha256(workspace: Path) -> str:
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


def render_agent_prompt(source_root: Path, condition: str) -> str:
    template = source_root / "examples/effect-experiment-native-v6/agent-task-template.txt"
    content = template.read_text(encoding="utf-8")
    policy_instruction = (
        "No frozen Skill snapshot is supplied for this condition."
        if condition == "no_skill"
        else "Read `frozen-policy.md` before editing and apply only that supplied frozen policy."
    )
    if "{policy_instruction}" not in content:
        raise ValueError("native V6 agent template lacks its policy placeholder")
    return content.replace("{policy_instruction}", policy_instruction)


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
        snapshot = source_root / f"examples/effect-experiment-native-v6/skills/{'old' if condition == 'old_skill' else 'new'}/frozen-policy.md"
        if not snapshot.is_file():
            raise FileNotFoundError(f"frozen policy snapshot is missing: {snapshot}")
        _ = shutil.copy2(snapshot, workspace / "frozen-policy.md")
    seed = initialize_git(workspace)
    prompt = render_agent_prompt(source_root, condition)
    prompt_path = raw_condition / "agent-prompt.txt"
    prompt_path.write_text(prompt, encoding="utf-8")
    handoff = workspace_input_sha256(workspace)
    task_input = {
        "task_id": task_id,
        "condition": condition,
        "workspace_tree_sha256": task["workspace_tree_sha256"],
        "frozen_policy_sha256": sha256(workspace / "frozen-policy.md") if condition != "no_skill" else None,
        "agent_prompt_sha256": sha256(prompt_path),
    }
    sequence: dict[str, object] = {
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
            "workspace_handoff_sha256": handoff,
            "condition_input_sha256": canonical_sha256(task_input),
        },
    )
    (raw_condition / "seed.txt").write_text(seed + "\n", encoding="utf-8")
    return PreparedCondition(task_id, condition, seed, predecessor_hashes)


def mark_agent_complete(
    raw_root: Path,
    task_id: str,
    condition: str,
    *,
    agent_id: str,
    model_id: str,
    started_at: str,
    finished_at: str,
    transcript: Path,
    executor_kind: str = "codex-native-subagent",
    exit_code: int | None = 0,
    auth_mode: str | None = None,
    skill_search_disabled: bool | None = None,
    codex_cli_version: str | None = None,
) -> None:
    directory = raw_root / task_id / condition
    if {entry.name for entry in directory.iterdir()} != PREPARE_ARTIFACTS:
        raise ValueError("agent completion requires exactly the prepared artifacts")
    if executor_kind not in EXECUTOR_KINDS:
        raise ValueError("executor_kind is not supported by the V6 protocol")
    if executor_kind == "codex-native-subagent" and (not agent_id.startswith("/root/") or len(agent_id) <= len("/root/")):
        raise ValueError("agent_id must identify a native subagent under /root/")
    if executor_kind == "codex-cli-api-key" and not agent_id.startswith("codex-cli:"):
        raise ValueError("agent_id must identify a Codex CLI condition")
    if isinstance(exit_code, bool) or (exit_code is not None and not isinstance(exit_code, int)):
        raise ValueError("exit_code must be an integer or null")
    if executor_kind == "codex-cli-api-key":
        if auth_mode != "api-key" or skill_search_disabled is not True or not codex_cli_version:
            raise ValueError("Codex CLI provenance requires api-key mode, disabled Skill search, and a CLI version")
    if not model_id:
        raise ValueError("model_id must be non-empty")
    for value, label in ((started_at, "started_at"), (finished_at, "finished_at")):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError(f"{label} must be an RFC 3339 timestamp") from error
        if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
            raise ValueError(f"{label} must be UTC")
    if started_at > finished_at:
        raise ValueError("agent timestamps must be ordered")
    if not transcript.is_file():
        raise FileNotFoundError(f"agent transcript is missing: {transcript}")
    transcript_target = directory / "agent-transcript.md"
    _ = shutil.copy2(transcript, transcript_target)
    if not transcript_target.read_text(encoding="utf-8").strip():
        raise ValueError("agent transcript must be non-empty")
    prepare = load_json(directory / "prepare.json")
    write_json(
        directory / "agent-result.json",
        {
            "status": "agent_exited",
            "task_id": task_id,
            "condition": condition,
            "executor": {
                "kind": executor_kind,
                "agent_id": agent_id,
                "model_id": model_id,
                "started_at": started_at,
                "finished_at": finished_at,
                "exit_code": exit_code,
                "agent_prompt_sha256": sha256(directory / "agent-prompt.txt"),
                "condition_input_sha256": prepare["condition_input_sha256"],
                "workspace_handoff_sha256": prepare["workspace_handoff_sha256"],
                "transcript_sha256": sha256(transcript_target),
                **(
                    {
                        "auth_mode": auth_mode,
                        "skill_search_disabled": skill_search_disabled,
                        "codex_cli_version": codex_cli_version,
                    }
                    if executor_kind == "codex-cli-api-key"
                    else {}
                ),
            },
        },
    )


def score_condition(corpus: Path, raw_root: Path, task_id: str, condition: str, workspace: Path) -> dict[str, object]:
    directory = raw_root / task_id / condition
    required_before_score = PREPARE_ARTIFACTS | {"agent-result.json", "agent-transcript.md"}
    if {entry.name for entry in directory.iterdir()} != required_before_score:
        raise ValueError("scoring requires a completed prepared condition with no prior score artifacts")
    seed = (directory / "seed.txt").read_text(encoding="utf-8").strip()
    if len(seed) != 40:
        raise ValueError("seed.txt must contain a Git commit SHA")
    (directory / "candidate.diff").write_text(capture_candidate_diff(workspace, seed), encoding="utf-8")
    task = manifest_task(corpus, task_id)
    score = score_trial(corpus, task_id, workspace, seed)
    # This is an execution fact, separate from whether the candidate passed
    # implementation-integrity or hidden-contract checks.
    score["scored_after_agent_exit"] = True
    score["scorer_provenance"] = {
        "base_runner_path": "scripts/native_cleanup_effect_runner_v1.py",
        "base_runner_sha256": sha256(Path(__file__).with_name("native_cleanup_effect_runner_v1.py")),
        "corpus_manifest_sha256": sha256(corpus / "manifest.json"),
        "hidden_tests_path": task["hidden_tests_path"],
        "hidden_tests_tree_sha256": task["hidden_tests_tree_sha256"],
        "reference_tree_sha256": task["reference_tree_sha256"],
        "workspace_tree_sha256": task["workspace_tree_sha256"],
    }
    score["pre_score_artifact_sha256"] = {
        name: sha256(directory / name)
        for name in ("sequence.json", "prepare.json", "seed.txt", "agent-prompt.txt", "agent-transcript.md", "agent-result.json", "candidate.diff")
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
    complete.add_argument("--agent-id", required=True)
    complete.add_argument("--model-id", required=True)
    complete.add_argument("--started-at", required=True)
    complete.add_argument("--finished-at", required=True)
    complete.add_argument("--transcript", type=Path, required=True)
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
        mark_agent_complete(
            args.raw_root,
            args.task,
            args.condition,
            agent_id=args.agent_id,
            model_id=args.model_id,
            started_at=args.started_at,
            finished_at=args.finished_at,
            transcript=args.transcript,
        )
    else:
        print(json.dumps(score_condition(args.corpus, args.raw_root, args.task, args.condition, args.workspace), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
