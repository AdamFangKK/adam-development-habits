#!/usr/bin/env python3
"""Run the isolated, absolute-artifact V8 paired Skill-effect protocol."""

# pyright: reportMissingTypeStubs=false

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import cast

import audit_effect_isolation_v8 as isolation
import run_effect_experiment_v6 as protocol


DEFAULT_MODEL_ID = "gpt-5.6-terra"
DEFAULT_HARNESS_ID = "codex-cli-0.147.0-alpha.1.2;exec;workspace-write;ephemeral;skill-search-disabled;absolute-output;checkpointed-v8"
DEFAULT_CODEX = str(Path(__file__).with_name("codex_v8_isolated.py").resolve())


def normalize_path_arguments(arguments: list[str]) -> list[str]:
    """Make every protocol path independent of the agent's temporary cwd."""
    path_flags = {"--corpus", "--prompts", "--skill", "--preregistration", "--raw-output", "--output"}
    normalized: list[str] = []
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        normalized.append(argument)
        if argument in path_flags:
            if index + 1 >= len(arguments):
                raise ValueError(f"{argument} requires a path")
            normalized.append(str(Path(arguments[index + 1]).expanduser().resolve()))
            index += 2
            continue
        index += 1
    return normalized


def v8_arguments(arguments: list[str]) -> list[str]:
    normalized = normalize_path_arguments(arguments)
    if "--codex" not in normalized:
        normalized[0:0] = ["--codex", DEFAULT_CODEX]
    return normalized


def record_isolation_failure(result_path: Path, report: dict[str, object]) -> None:
    result = isolation.load_object(result_path)
    collection_value = result.get("collection")
    collection = cast(dict[str, object], collection_value) if isinstance(collection_value, dict) else {}
    collection["ineligible_reason"] = "V8 isolation audit failed; no effect analysis or retry is allowed."
    collection["isolation_audit"] = report
    collection["isolation_audit_passed"] = False
    result["collection"] = collection
    result["status"] = "interrupted"
    _ = result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def record_isolation_success(result_path: Path, report: dict[str, object]) -> None:
    """Attach the successful V8 audit before a result becomes analyzable."""
    result = isolation.load_object(result_path)
    collection_value = result.get("collection")
    collection = cast(dict[str, object], collection_value) if isinstance(collection_value, dict) else {}
    collection["isolation_audit"] = report
    collection["isolation_audit_passed"] = True
    result["collection"] = collection
    _ = result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def score_candidate(
    *,
    run_root: Path,
    task: protocol.TaskRecord,
    corpus: Path,
    timeout: float,
) -> dict[str, object]:
    """Invoke the versioned V8 hidden scorer without exposing it to the agent."""
    command = [
        sys.executable,
        str(Path(__file__).with_name("score_effect_workspace_v8.py")),
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
        result = subprocess.run(
            command,
            env=protocol.environment(),
            capture_output=True,
            text=True,
            timeout=timeout + 5,
            check=False,
        )
        return cast(dict[str, object], json.loads(result.stdout))
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        return {"passed": False, "returncode": None, "stdout": "", "stderr": str(error), "timeout": True}


def main() -> int:
    original_score_candidate = protocol.score_candidate
    original_model_id = protocol.DEFAULT_MODEL_ID
    original_harness_id = protocol.DEFAULT_HARNESS_ID
    original_argv = sys.argv[:]
    normalized = v8_arguments(sys.argv[1:])
    sys.argv[1:] = normalized
    protocol.score_candidate = score_candidate
    protocol.DEFAULT_MODEL_ID = DEFAULT_MODEL_ID
    protocol.DEFAULT_HARNESS_ID = DEFAULT_HARNESS_ID
    try:
        exit_code = protocol.main()
        values = {normalized[index]: normalized[index + 1] for index in range(len(normalized) - 1) if normalized[index].startswith("--") and normalized[index] in {"--raw-output", "--output", "--skill"}}
        raw_root = Path(values["--raw-output"])
        result_path = Path(values["--output"])
        report = isolation.audit_collection(raw_root, result_path, Path(values["--skill"]))
        if not bool(report["passed"]):
            record_isolation_failure(result_path, report)
            return 2
        record_isolation_success(result_path, report)
        return exit_code
    finally:
        sys.argv[:] = original_argv
        protocol.score_candidate = original_score_candidate
        protocol.DEFAULT_MODEL_ID = original_model_id
        protocol.DEFAULT_HARNESS_ID = original_harness_id


if __name__ == "__main__":
    raise SystemExit(main())
