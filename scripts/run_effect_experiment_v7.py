#!/usr/bin/env python3
"""Run a checkpointed paired v7 Codex repair experiment on a fresh corpus."""

from __future__ import annotations

# The v7 entry point delegates its stable mechanics to the frozen v6 runner.
# pyright: reportMissingTypeStubs=false

import json
import subprocess
import sys
from pathlib import Path
from typing import cast

import run_effect_experiment_v6 as protocol


DEFAULT_MODEL_ID = "gpt-5.6-terra"
DEFAULT_HARNESS_ID = "codex-cli-0.147.0-alpha.1.2;exec;workspace-write;ephemeral;checkpointed-v7"


def score_candidate(
    *,
    run_root: Path,
    task: protocol.TaskRecord,
    corpus: Path,
    timeout: float,
) -> dict[str, object]:
    command = [
        sys.executable,
        str(Path(__file__).with_name("score_effect_workspace_v7.py")),
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
        result = subprocess.run(command, env=protocol.environment(), capture_output=True, text=True, timeout=timeout + 5, check=False)
        return cast(dict[str, object], json.loads(result.stdout))
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        return {"passed": False, "returncode": None, "stdout": "", "stderr": str(error), "timeout": True}


def main() -> int:
    # Patch only while the delegated process runs, then restore v6 for long-lived callers.
    original_score_candidate = protocol.score_candidate
    original_model_id = protocol.DEFAULT_MODEL_ID
    original_harness_id = protocol.DEFAULT_HARNESS_ID
    protocol.score_candidate = score_candidate
    protocol.DEFAULT_MODEL_ID = DEFAULT_MODEL_ID
    protocol.DEFAULT_HARNESS_ID = DEFAULT_HARNESS_ID
    try:
        return protocol.main()
    finally:
        protocol.score_candidate = original_score_candidate
        protocol.DEFAULT_MODEL_ID = original_model_id
        protocol.DEFAULT_HARNESS_ID = original_harness_id


if __name__ == "__main__":
    raise SystemExit(main())
