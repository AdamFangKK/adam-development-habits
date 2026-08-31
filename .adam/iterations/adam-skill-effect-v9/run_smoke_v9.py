#!/usr/bin/env python3
"""Run a retained non-corpus V9 wrapper smoke across all three conditions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_effect_isolation_v9 import audit_collection  # noqa: E402
from run_effect_experiment_v9 import (  # noqa: E402
    Arguments,
    DEFAULT_CODEX,
    DEFAULT_HARNESS_ID,
    DEFAULT_MODEL_ID,
    TaskRecord,
    atomic_write_json,
    execute_task_block,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("--run-id", required=True, choices=("smoke-002", "smoke-003", "smoke-004"))
    options = parser.parse_args()
    smoke_root = ROOT / "examples" / "effect-experiment-v9" / "smoke"
    evidence_root = ROOT / ".adam" / "iterations" / "adam-skill-effect-v9" / options.run_id
    raw_root = evidence_root / "raw"
    result_path = evidence_root / "result.json"
    if evidence_root.exists():
        raise FileExistsError(f"refusing to overwrite retained smoke evidence: {evidence_root}")
    arguments = Arguments(
        corpus=smoke_root,
        prompts=ROOT / "examples" / "effect-experiment-v9" / "prompts",
        old_skill=ROOT / "examples" / "effect-experiment-v9" / "skills" / "old" / "SKILL.md",
        new_skill=ROOT / "examples" / "effect-experiment-v9" / "skills" / "new" / "SKILL.md",
        preregistration=result_path,
        preregistration_commit="0" * 40,
        raw_output=raw_root,
        output=result_path,
        seed=0,
        codex=DEFAULT_CODEX,
        model=DEFAULT_MODEL_ID,
        harness=DEFAULT_HARNESS_ID,
        agent_timeout=420.0,
        test_timeout=30.0,
        preflight=False,
    )
    task = TaskRecord(
        task_id="rotation",
        cohort="smoke",
        stratum="single-module",
        workspace_path="tasks/rotation",
        hidden_tests_path="hidden-tests/rotation",
        allowed_edit_paths=("policy.py",),
        public_command=("python3", "-m", "unittest", "discover", "-s", "tests"),
        hidden_command=("python3", "-m", "unittest", "discover", "-s", "tests"),
        execution_order=("no_skill", "old_skill", "new_skill"),
    )
    raw_root.mkdir(parents=True)
    trials = execute_task_block(
        task=task,
        corpus=smoke_root,
        prompts=arguments.prompts,
        skill_snapshots={
            "old_skill": arguments.old_skill,
            "new_skill": arguments.new_skill,
        },
        raw_root=raw_root,
        arguments=arguments,
    )
    result: dict[str, object] = {
        "schema_version": 1,
        "experiment_id": f"adam-skill-effect-v9-{options.run_id}",
        "status": "completed" if all(trial["trial_complete"] for trial in trials) else "interrupted",
        "model_id": arguments.model,
        "harness_id": arguments.harness,
        "task_plan": {"tasks": [{"task_id": task.task_id}]},
        "trials": trials,
    }
    atomic_write_json(result_path, result)
    audit = audit_collection(
        raw_root,
        result_path,
        old_skill=arguments.old_skill,
        new_skill=arguments.new_skill,
        corpus=smoke_root,
    )
    _ = (evidence_root / "isolation-audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    passed = (
        result["status"] == "completed"
        and audit["passed"] is True
        and all(trial["hidden_repair_pass"] for trial in trials)
    )
    print(json.dumps({"passed": passed, "audit": audit, "trials": trials}, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
